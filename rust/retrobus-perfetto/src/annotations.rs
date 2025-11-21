use perfetto_writer::EventBuilder;

type Writer = Vec<u8>;

/// Values that can be attached as Perfetto debug annotations.
#[derive(Debug, Clone)]
pub enum AnnotationValue {
    Bool(bool),
    Int(i64),
    UInt(u64),
    Double(f64),
    Str(String),
    Pointer(u64),
}

impl From<bool> for AnnotationValue {
    fn from(value: bool) -> Self {
        AnnotationValue::Bool(value)
    }
}

impl From<i64> for AnnotationValue {
    fn from(value: i64) -> Self {
        AnnotationValue::Int(value)
    }
}

impl From<u64> for AnnotationValue {
    fn from(value: u64) -> Self {
        AnnotationValue::UInt(value)
    }
}

impl From<i32> for AnnotationValue {
    fn from(value: i32) -> Self {
        AnnotationValue::Int(value as i64)
    }
}

impl From<u32> for AnnotationValue {
    fn from(value: u32) -> Self {
        AnnotationValue::UInt(value as u64)
    }
}

impl From<f64> for AnnotationValue {
    fn from(value: f64) -> Self {
        AnnotationValue::Double(value)
    }
}

impl From<f32> for AnnotationValue {
    fn from(value: f32) -> Self {
        AnnotationValue::Double(value as f64)
    }
}

impl From<String> for AnnotationValue {
    fn from(value: String) -> Self {
        AnnotationValue::Str(value)
    }
}

impl From<&str> for AnnotationValue {
    fn from(value: &str) -> Self {
        AnnotationValue::Str(value.to_string())
    }
}

impl From<&String> for AnnotationValue {
    fn from(value: &String) -> Self {
        AnnotationValue::Str(value.clone())
    }
}

const POINTER_SUFFIXES: [&str; 5] = ["_addr", "_address", "_pc", "_sp", "_pointer"];

fn is_pointer_field(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    POINTER_SUFFIXES
        .iter()
        .any(|suffix| lower.ends_with(suffix))
        || lower == "pc"
        || lower == "sp"
        || lower == "address"
}

pub(crate) fn apply_annotation(
    name: &str,
    value: AnnotationValue,
    event: &mut EventBuilder<'_, Writer>,
) {
    match value {
        AnnotationValue::Pointer(ptr) => event.debug_pointer(name, ptr),
        AnnotationValue::Bool(v) => event.debug_bool(name, v),
        AnnotationValue::Int(v) => {
            if is_pointer_field(name) {
                event.debug_pointer(name, v as u64);
            } else {
                event.debug_int(name, v);
            }
        }
        AnnotationValue::UInt(v) => {
            if is_pointer_field(name) {
                event.debug_pointer(name, v);
            } else {
                event.debug_uint(name, v);
            }
        }
        AnnotationValue::Double(v) => event.debug_double(name, v),
        AnnotationValue::Str(v) => event.debug_str(name, v),
    }
}
