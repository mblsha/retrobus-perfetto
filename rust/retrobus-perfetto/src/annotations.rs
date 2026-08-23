use perfetto_writer::EventBuilder;
use std::error::Error;
use std::fmt;

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
    Dictionary(Vec<(String, AnnotationValue)>),
    Array(Vec<AnnotationValue>),
}

impl AnnotationValue {
    pub fn dictionary(entries: impl IntoIterator<Item = (String, AnnotationValue)>) -> Self {
        Self::Dictionary(entries.into_iter().collect())
    }

    pub fn array(values: impl IntoIterator<Item = AnnotationValue>) -> Self {
        Self::Array(values.into_iter().collect())
    }

    pub fn pointer(value: u64) -> Self {
        Self::Pointer(value)
    }

    pub(crate) fn validate_depth(&self, max_depth: usize) -> Result<(), AnnotationError> {
        self.validate_at_depth(0, max_depth)
    }

    fn validate_at_depth(
        &self,
        current_depth: usize,
        max_depth: usize,
    ) -> Result<(), AnnotationError> {
        match self {
            Self::Dictionary(entries) => {
                if current_depth >= max_depth {
                    return Err(AnnotationError::DepthExceeded { max_depth });
                }
                for (_, value) in entries {
                    value.validate_at_depth(current_depth + 1, max_depth)?;
                }
            }
            Self::Array(values) => {
                if current_depth >= max_depth {
                    return Err(AnnotationError::DepthExceeded { max_depth });
                }
                for value in values {
                    value.validate_at_depth(current_depth + 1, max_depth)?;
                }
            }
            _ => {}
        }
        Ok(())
    }

    fn to_debug_value(&self, name: Option<&str>) -> perfetto_writer::DebugValue {
        match self {
            Self::Bool(value) => perfetto_writer::DebugValue::Bool(*value),
            Self::Int(value) if name.is_some_and(is_pointer_field) => {
                perfetto_writer::DebugValue::Pointer(*value as u64)
            }
            Self::Int(value) => perfetto_writer::DebugValue::Int(*value),
            Self::UInt(value) if name.is_some_and(is_pointer_field) => {
                perfetto_writer::DebugValue::Pointer(*value)
            }
            Self::UInt(value) => perfetto_writer::DebugValue::UInt(*value),
            Self::Double(value) => perfetto_writer::DebugValue::Double(*value),
            Self::Str(value) => perfetto_writer::DebugValue::String(value.clone()),
            Self::Pointer(value) => perfetto_writer::DebugValue::Pointer(*value),
            Self::Dictionary(entries) => perfetto_writer::DebugValue::Dictionary(
                entries
                    .iter()
                    .map(|(key, value)| (key.clone(), value.to_debug_value(Some(key))))
                    .collect(),
            ),
            Self::Array(values) => perfetto_writer::DebugValue::Array(
                values
                    .iter()
                    .map(|value| value.to_debug_value(None))
                    .collect(),
            ),
        }
    }
}

impl From<Vec<AnnotationValue>> for AnnotationValue {
    fn from(value: Vec<AnnotationValue>) -> Self {
        Self::Array(value)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AnnotationError {
    DepthExceeded { max_depth: usize },
}

impl fmt::Display for AnnotationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::DepthExceeded { max_depth } => write!(
                formatter,
                "debug annotation nesting exceeds {max_depth} containers"
            ),
        }
    }
}

impl Error for AnnotationError {}

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
    event.debug_value(name, &value.to_debug_value(Some(name)));
}
