use std::cell::UnsafeCell;
use std::marker::PhantomData;
use std::rc::Rc;
use std::sync::{Condvar, Mutex};
use std::thread::ThreadId;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum BorrowState {
    Unborrowed,
    Shared(usize),
    Mutable,
}

#[derive(Debug)]
struct State {
    owner: Option<ThreadId>,
    depth: usize,
    borrow: BorrowState,
}

impl State {
    const fn new() -> Self {
        Self {
            owner: None,
            depth: 0,
            borrow: BorrowState::Unborrowed,
        }
    }
}

/// Reentrant handle intended for global emulator instrumentation (nested tracing).
///
/// Unlike `Mutex<T>`, this supports re-entrant `enter()` on the owning thread. Access to the
/// inner value is provided via scoped closures (`with_ref` / `with_mut`) so references cannot
/// escape and alias across nested enters.
pub struct ReentrantHandle<T> {
    state: Mutex<State>,
    available: Condvar,
    inner: UnsafeCell<T>,
}

/// Guard returned by [`ReentrantHandle::enter`].
///
/// The guard is not `Send` to prevent dropping/accessing it from a different thread.
pub struct ReentrantGuard<'a, T> {
    handle: &'a ReentrantHandle<T>,
    owner: ThreadId,
    _not_send: PhantomData<Rc<()>>,
}

impl<T> ReentrantHandle<T> {
    pub const fn new(inner: T) -> Self {
        Self {
            state: Mutex::new(State::new()),
            available: Condvar::new(),
            inner: UnsafeCell::new(inner),
        }
    }

    /// Enter the handle, blocking if another thread is currently inside.
    pub fn enter(&self) -> ReentrantGuard<'_, T> {
        let tid = std::thread::current().id();
        let mut state = self.state.lock().unwrap_or_else(|e| e.into_inner());

        loop {
            match state.owner {
                None => {
                    state.owner = Some(tid);
                    state.depth = 1;
                    break;
                }
                Some(owner) if owner == tid => {
                    state.depth = state.depth.saturating_add(1);
                    break;
                }
                Some(_) => {
                    state = self
                        .available
                        .wait(state)
                        .unwrap_or_else(|e| e.into_inner());
                }
            }
        }

        ReentrantGuard {
            handle: self,
            owner: tid,
            _not_send: PhantomData,
        }
    }

    /// Enter the handle only if it is uncontended or already owned by the current thread.
    pub fn try_enter(&self) -> Option<ReentrantGuard<'_, T>> {
        let tid = std::thread::current().id();
        let mut state = self.state.lock().unwrap_or_else(|e| e.into_inner());

        match state.owner {
            None => {
                state.owner = Some(tid);
                state.depth = 1;
                Some(ReentrantGuard {
                    handle: self,
                    owner: tid,
                    _not_send: PhantomData,
                })
            }
            Some(owner) if owner == tid => {
                state.depth = state.depth.saturating_add(1);
                Some(ReentrantGuard {
                    handle: self,
                    owner: tid,
                    _not_send: PhantomData,
                })
            }
            Some(_) => None,
        }
    }

    /// Enter the handle, panicking if another thread currently owns it.
    pub fn enter_strict(&self) -> ReentrantGuard<'_, T> {
        let tid = std::thread::current().id();
        let mut state = self.state.lock().unwrap_or_else(|e| e.into_inner());
        match state.owner {
            None => {
                state.owner = Some(tid);
                state.depth = 1;
            }
            Some(owner) if owner == tid => {
                state.depth = state.depth.saturating_add(1);
            }
            Some(owner) => {
                panic!(
                    "ReentrantHandle used from multiple threads (owner={owner:?}, current={tid:?})"
                );
            }
        }

        ReentrantGuard {
            handle: self,
            owner: tid,
            _not_send: PhantomData,
        }
    }

    /// Convenience for `enter().with_ref(...)`.
    pub fn with_ref<R>(&self, f: impl for<'b> FnOnce(&'b T) -> R) -> R {
        let guard = self.enter();
        guard.with_ref(f)
    }

    /// Convenience for `enter().with_mut(...)`.
    pub fn with_mut<R>(&self, f: impl for<'b> FnOnce(&'b mut T) -> R) -> R {
        let mut guard = self.enter();
        guard.with_mut(f)
    }

    /// Replace the inner value, returning the previous value.
    pub fn replace(&self, value: T) -> T {
        self.with_mut(|inner| std::mem::replace(inner, value))
    }

    /// Take the inner value, leaving `T::default()` in its place.
    pub fn take(&self) -> T
    where
        T: Default,
    {
        self.with_mut(std::mem::take)
    }
}

impl<T> Default for ReentrantHandle<T>
where
    T: Default,
{
    fn default() -> Self {
        Self::new(T::default())
    }
}

unsafe impl<T: Send> Sync for ReentrantHandle<T> {}
unsafe impl<T: Send> Send for ReentrantHandle<T> {}

struct BorrowGuard<'a, T> {
    handle: &'a ReentrantHandle<T>,
    kind: BorrowState,
}

impl<'a, T> Drop for BorrowGuard<'a, T> {
    fn drop(&mut self) {
        let mut state = self.handle.state.lock().unwrap_or_else(|e| e.into_inner());
        match (self.kind, state.borrow) {
            (BorrowState::Mutable, _) => state.borrow = BorrowState::Unborrowed,
            (BorrowState::Shared(_), BorrowState::Shared(n)) if n > 1 => {
                state.borrow = BorrowState::Shared(n - 1);
            }
            (BorrowState::Shared(_), BorrowState::Shared(_)) => {
                state.borrow = BorrowState::Unborrowed;
            }
            _ => {
                state.borrow = BorrowState::Unborrowed;
            }
        }
    }
}

impl<'a, T> ReentrantGuard<'a, T> {
    /// Run `f` with a shared borrow of the inner value.
    pub fn with_ref<R>(&self, f: impl for<'b> FnOnce(&'b T) -> R) -> R {
        let mut state = self.handle.state.lock().unwrap_or_else(|e| e.into_inner());
        debug_assert_eq!(state.owner, Some(self.owner));

        match state.borrow {
            BorrowState::Mutable => panic!("ReentrantHandle is already mutably borrowed"),
            BorrowState::Unborrowed => state.borrow = BorrowState::Shared(1),
            BorrowState::Shared(n) => state.borrow = BorrowState::Shared(n + 1),
        }
        drop(state);

        let _borrow = BorrowGuard {
            handle: self.handle,
            kind: BorrowState::Shared(1),
        };
        let value = unsafe { &*self.handle.inner.get() };
        f(value)
    }

    /// Run `f` with an exclusive borrow of the inner value.
    pub fn with_mut<R>(&mut self, f: impl for<'b> FnOnce(&'b mut T) -> R) -> R {
        let mut state = self.handle.state.lock().unwrap_or_else(|e| e.into_inner());
        debug_assert_eq!(state.owner, Some(self.owner));

        if state.borrow != BorrowState::Unborrowed {
            panic!("ReentrantHandle is already borrowed");
        }
        state.borrow = BorrowState::Mutable;
        drop(state);

        let _borrow = BorrowGuard {
            handle: self.handle,
            kind: BorrowState::Mutable,
        };
        let value = unsafe { &mut *self.handle.inner.get() };
        f(value)
    }

    /// Replace the inner value, returning the previous value.
    pub fn replace(&mut self, value: T) -> T {
        self.with_mut(|inner| std::mem::replace(inner, value))
    }

    /// Take the inner value, leaving `T::default()` in its place.
    pub fn take(&mut self) -> T
    where
        T: Default,
    {
        self.with_mut(std::mem::take)
    }
}

impl<T> ReentrantGuard<'_, Option<T>> {
    /// Run `f` only when the inner value is `Some`.
    pub fn with_some<R>(&mut self, f: impl for<'b> FnOnce(&'b mut T) -> R) -> Option<R> {
        self.with_mut(|opt| opt.as_mut().map(|value| f(value)))
    }
}

impl<T> ReentrantHandle<Option<T>> {
    /// Run `f` only when the inner value is `Some`.
    pub fn with_some<R>(&self, f: impl for<'b> FnOnce(&'b mut T) -> R) -> Option<R> {
        let mut guard = self.enter();
        guard.with_some(f)
    }
}

impl<'a, T> Drop for ReentrantGuard<'a, T> {
    fn drop(&mut self) {
        let mut state = self.handle.state.lock().unwrap_or_else(|e| e.into_inner());

        if state.owner != Some(self.owner) {
            debug_assert_eq!(state.owner, Some(self.owner));
            return;
        }

        if state.depth > 1 {
            state.depth -= 1;
            return;
        }

        state.owner = None;
        state.depth = 0;
        state.borrow = BorrowState::Unborrowed;
        drop(state);
        self.handle.available.notify_one();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{mpsc, Arc, Barrier};

    #[test]
    fn nested_enter_allows_scoped_mutation() {
        let handle = ReentrantHandle::new(Vec::<u32>::new());

        let mut outer = handle.enter();
        outer.with_mut(|v| v.push(1));

        let mut inner = handle.enter();
        inner.with_mut(|v| v.push(2));
        drop(inner);

        outer.with_mut(|v| v.push(3));
        drop(outer);

        handle.with_ref(|v| assert_eq!(v.as_slice(), &[1, 2, 3]));
    }

    #[test]
    fn try_enter_fails_while_other_thread_holds_guard() {
        let handle = Arc::new(ReentrantHandle::new(0u32));
        let root = handle.enter();

        let barrier = Arc::new(Barrier::new(2));
        let (tx, rx) = mpsc::channel();

        let handle_clone = Arc::clone(&handle);
        let barrier_clone = Arc::clone(&barrier);
        let t = std::thread::spawn(move || {
            barrier_clone.wait();
            assert!(handle_clone.try_enter().is_none());
            tx.send(()).unwrap();
        });

        barrier.wait();
        rx.recv().unwrap();
        drop(root);
        t.join().unwrap();
    }

    #[test]
    fn enter_blocks_until_released() {
        let handle = Arc::new(ReentrantHandle::new(0u32));
        let root = handle.enter();

        let (tx, rx) = mpsc::channel();
        let handle_clone = Arc::clone(&handle);
        let t = std::thread::spawn(move || {
            tx.send("waiting").unwrap();
            let mut guard = handle_clone.enter();
            guard.with_mut(|v| *v = 7);
            tx.send("acquired").unwrap();
        });

        assert_eq!(rx.recv().unwrap(), "waiting");
        drop(root);
        assert_eq!(rx.recv().unwrap(), "acquired");
        t.join().unwrap();

        handle.with_ref(|v| assert_eq!(*v, 7));
    }

    #[test]
    fn borrow_conflict_panics_but_recovers() {
        let handle = ReentrantHandle::new(0u32);
        let mut guard = handle.enter();

        let res = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            guard.with_mut(|v| {
                let mut nested = handle.enter();
                let _ = nested.with_mut(|v2| *v2 = 1);
                *v = 2;
            });
        }));
        assert!(res.is_err());

        handle.with_mut(|v| *v = 9);
        handle.with_ref(|v| assert_eq!(*v, 9));
    }

    #[test]
    fn strict_panics_on_cross_thread_use() {
        let handle = Arc::new(ReentrantHandle::new(0u32));
        let _root = handle.enter();

        let handle_clone = Arc::clone(&handle);
        let t = std::thread::spawn(move || {
            let _ = handle_clone.enter_strict();
        });

        assert!(t.join().is_err());
    }
}
