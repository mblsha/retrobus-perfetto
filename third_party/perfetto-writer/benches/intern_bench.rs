use criterion::{Criterion, criterion_group, criterion_main};

fn bench_intern_first_occurrence(c: &mut Criterion) {
    c.bench_function("single_entry", |_| {
        // black_box(intern.intern("test_string"));
    });
}

criterion_group!(benches, bench_intern_first_occurrence,);
criterion_main!(benches);
