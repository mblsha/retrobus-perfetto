import * as $protobuf from "protobufjs";
import Long = require("long");
/** Namespace perfetto. */
export namespace perfetto {

    /** Namespace protos. */
    namespace protos {

        /** Properties of an EventName. */
        interface IEventName {

            /** EventName iid */
            iid?: (number|Long|null);

            /** EventName name */
            name?: (string|null);
        }

        /** Represents an EventName. */
        class EventName implements IEventName {

            /**
             * Constructs a new EventName.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.IEventName);

            /** EventName iid. */
            public iid: (number|Long);

            /** EventName name. */
            public name: string;

            /**
             * Creates a new EventName instance using the specified properties.
             * @param [properties] Properties to set
             * @returns EventName instance
             */
            public static create(properties?: perfetto.protos.IEventName): perfetto.protos.EventName;

            /**
             * Encodes the specified EventName message. Does not implicitly {@link perfetto.protos.EventName.verify|verify} messages.
             * @param message EventName message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.IEventName, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified EventName message, length delimited. Does not implicitly {@link perfetto.protos.EventName.verify|verify} messages.
             * @param message EventName message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.IEventName, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes an EventName message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns EventName
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.EventName;

            /**
             * Decodes an EventName message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns EventName
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.EventName;

            /**
             * Verifies an EventName message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates an EventName message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns EventName
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.EventName;

            /**
             * Creates a plain object from an EventName message. Also converts values to other types if specified.
             * @param message EventName
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.EventName, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this EventName to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for EventName
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        /** Properties of a DebugAnnotationName. */
        interface IDebugAnnotationName {

            /** DebugAnnotationName iid */
            iid?: (number|Long|null);

            /** DebugAnnotationName name */
            name?: (string|null);
        }

        /** Represents a DebugAnnotationName. */
        class DebugAnnotationName implements IDebugAnnotationName {

            /**
             * Constructs a new DebugAnnotationName.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.IDebugAnnotationName);

            /** DebugAnnotationName iid. */
            public iid: (number|Long);

            /** DebugAnnotationName name. */
            public name: string;

            /**
             * Creates a new DebugAnnotationName instance using the specified properties.
             * @param [properties] Properties to set
             * @returns DebugAnnotationName instance
             */
            public static create(properties?: perfetto.protos.IDebugAnnotationName): perfetto.protos.DebugAnnotationName;

            /**
             * Encodes the specified DebugAnnotationName message. Does not implicitly {@link perfetto.protos.DebugAnnotationName.verify|verify} messages.
             * @param message DebugAnnotationName message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.IDebugAnnotationName, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified DebugAnnotationName message, length delimited. Does not implicitly {@link perfetto.protos.DebugAnnotationName.verify|verify} messages.
             * @param message DebugAnnotationName message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.IDebugAnnotationName, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a DebugAnnotationName message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns DebugAnnotationName
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.DebugAnnotationName;

            /**
             * Decodes a DebugAnnotationName message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns DebugAnnotationName
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.DebugAnnotationName;

            /**
             * Verifies a DebugAnnotationName message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a DebugAnnotationName message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns DebugAnnotationName
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.DebugAnnotationName;

            /**
             * Creates a plain object from a DebugAnnotationName message. Also converts values to other types if specified.
             * @param message DebugAnnotationName
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.DebugAnnotationName, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this DebugAnnotationName to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for DebugAnnotationName
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        /** Properties of an InternedString. */
        interface IInternedString {

            /** InternedString iid */
            iid?: (number|Long|null);

            /** InternedString str */
            str?: (Uint8Array|null);
        }

        /** Represents an InternedString. */
        class InternedString implements IInternedString {

            /**
             * Constructs a new InternedString.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.IInternedString);

            /** InternedString iid. */
            public iid: (number|Long);

            /** InternedString str. */
            public str: Uint8Array;

            /**
             * Creates a new InternedString instance using the specified properties.
             * @param [properties] Properties to set
             * @returns InternedString instance
             */
            public static create(properties?: perfetto.protos.IInternedString): perfetto.protos.InternedString;

            /**
             * Encodes the specified InternedString message. Does not implicitly {@link perfetto.protos.InternedString.verify|verify} messages.
             * @param message InternedString message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.IInternedString, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified InternedString message, length delimited. Does not implicitly {@link perfetto.protos.InternedString.verify|verify} messages.
             * @param message InternedString message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.IInternedString, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes an InternedString message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns InternedString
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.InternedString;

            /**
             * Decodes an InternedString message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns InternedString
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.InternedString;

            /**
             * Verifies an InternedString message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates an InternedString message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns InternedString
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.InternedString;

            /**
             * Creates a plain object from an InternedString message. Also converts values to other types if specified.
             * @param message InternedString
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.InternedString, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this InternedString to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for InternedString
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        /** Properties of an InternedData. */
        interface IInternedData {

            /** InternedData eventNames */
            eventNames?: (perfetto.protos.IEventName[]|null);

            /** InternedData debugAnnotationNames */
            debugAnnotationNames?: (perfetto.protos.IDebugAnnotationName[]|null);

            /** InternedData debugAnnotationStringValues */
            debugAnnotationStringValues?: (perfetto.protos.IInternedString[]|null);
        }

        /** Represents an InternedData. */
        class InternedData implements IInternedData {

            /**
             * Constructs a new InternedData.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.IInternedData);

            /** InternedData eventNames. */
            public eventNames: perfetto.protos.IEventName[];

            /** InternedData debugAnnotationNames. */
            public debugAnnotationNames: perfetto.protos.IDebugAnnotationName[];

            /** InternedData debugAnnotationStringValues. */
            public debugAnnotationStringValues: perfetto.protos.IInternedString[];

            /**
             * Creates a new InternedData instance using the specified properties.
             * @param [properties] Properties to set
             * @returns InternedData instance
             */
            public static create(properties?: perfetto.protos.IInternedData): perfetto.protos.InternedData;

            /**
             * Encodes the specified InternedData message. Does not implicitly {@link perfetto.protos.InternedData.verify|verify} messages.
             * @param message InternedData message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.IInternedData, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified InternedData message, length delimited. Does not implicitly {@link perfetto.protos.InternedData.verify|verify} messages.
             * @param message InternedData message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.IInternedData, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes an InternedData message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns InternedData
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.InternedData;

            /**
             * Decodes an InternedData message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns InternedData
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.InternedData;

            /**
             * Verifies an InternedData message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates an InternedData message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns InternedData
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.InternedData;

            /**
             * Creates a plain object from an InternedData message. Also converts values to other types if specified.
             * @param message InternedData
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.InternedData, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this InternedData to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for InternedData
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        /** Properties of a DebugAnnotation. */
        interface IDebugAnnotation {

            /** DebugAnnotation nameIid */
            nameIid?: (number|Long|null);

            /** DebugAnnotation name */
            name?: (string|null);

            /** DebugAnnotation boolValue */
            boolValue?: (boolean|null);

            /** DebugAnnotation uintValue */
            uintValue?: (number|Long|null);

            /** DebugAnnotation intValue */
            intValue?: (number|Long|null);

            /** DebugAnnotation doubleValue */
            doubleValue?: (number|null);

            /** DebugAnnotation pointerValue */
            pointerValue?: (number|Long|null);

            /** DebugAnnotation nestedValue */
            nestedValue?: (perfetto.protos.DebugAnnotation.INestedValue|null);

            /** DebugAnnotation legacyJsonValue */
            legacyJsonValue?: (string|null);

            /** DebugAnnotation stringValue */
            stringValue?: (string|null);

            /** DebugAnnotation stringValueIid */
            stringValueIid?: (number|Long|null);

            /** DebugAnnotation protoTypeName */
            protoTypeName?: (string|null);

            /** DebugAnnotation protoTypeNameIid */
            protoTypeNameIid?: (number|Long|null);

            /** DebugAnnotation protoValue */
            protoValue?: (Uint8Array|null);

            /** DebugAnnotation dictEntries */
            dictEntries?: (perfetto.protos.IDebugAnnotation[]|null);

            /** DebugAnnotation arrayValues */
            arrayValues?: (perfetto.protos.IDebugAnnotation[]|null);
        }

        /** Represents a DebugAnnotation. */
        class DebugAnnotation implements IDebugAnnotation {

            /**
             * Constructs a new DebugAnnotation.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.IDebugAnnotation);

            /** DebugAnnotation nameIid. */
            public nameIid?: (number|Long|null);

            /** DebugAnnotation name. */
            public name?: (string|null);

            /** DebugAnnotation boolValue. */
            public boolValue?: (boolean|null);

            /** DebugAnnotation uintValue. */
            public uintValue?: (number|Long|null);

            /** DebugAnnotation intValue. */
            public intValue?: (number|Long|null);

            /** DebugAnnotation doubleValue. */
            public doubleValue?: (number|null);

            /** DebugAnnotation pointerValue. */
            public pointerValue?: (number|Long|null);

            /** DebugAnnotation nestedValue. */
            public nestedValue?: (perfetto.protos.DebugAnnotation.INestedValue|null);

            /** DebugAnnotation legacyJsonValue. */
            public legacyJsonValue?: (string|null);

            /** DebugAnnotation stringValue. */
            public stringValue?: (string|null);

            /** DebugAnnotation stringValueIid. */
            public stringValueIid?: (number|Long|null);

            /** DebugAnnotation protoTypeName. */
            public protoTypeName?: (string|null);

            /** DebugAnnotation protoTypeNameIid. */
            public protoTypeNameIid?: (number|Long|null);

            /** DebugAnnotation protoValue. */
            public protoValue: Uint8Array;

            /** DebugAnnotation dictEntries. */
            public dictEntries: perfetto.protos.IDebugAnnotation[];

            /** DebugAnnotation arrayValues. */
            public arrayValues: perfetto.protos.IDebugAnnotation[];

            /** DebugAnnotation nameField. */
            public nameField?: ("nameIid"|"name");

            /** DebugAnnotation value. */
            public value?: ("boolValue"|"uintValue"|"intValue"|"doubleValue"|"pointerValue"|"nestedValue"|"legacyJsonValue"|"stringValue"|"stringValueIid");

            /** DebugAnnotation protoTypeDescriptor. */
            public protoTypeDescriptor?: ("protoTypeName"|"protoTypeNameIid");

            /**
             * Creates a new DebugAnnotation instance using the specified properties.
             * @param [properties] Properties to set
             * @returns DebugAnnotation instance
             */
            public static create(properties?: perfetto.protos.IDebugAnnotation): perfetto.protos.DebugAnnotation;

            /**
             * Encodes the specified DebugAnnotation message. Does not implicitly {@link perfetto.protos.DebugAnnotation.verify|verify} messages.
             * @param message DebugAnnotation message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.IDebugAnnotation, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified DebugAnnotation message, length delimited. Does not implicitly {@link perfetto.protos.DebugAnnotation.verify|verify} messages.
             * @param message DebugAnnotation message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.IDebugAnnotation, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a DebugAnnotation message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns DebugAnnotation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.DebugAnnotation;

            /**
             * Decodes a DebugAnnotation message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns DebugAnnotation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.DebugAnnotation;

            /**
             * Verifies a DebugAnnotation message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a DebugAnnotation message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns DebugAnnotation
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.DebugAnnotation;

            /**
             * Creates a plain object from a DebugAnnotation message. Also converts values to other types if specified.
             * @param message DebugAnnotation
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.DebugAnnotation, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this DebugAnnotation to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for DebugAnnotation
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        namespace DebugAnnotation {

            /** Properties of a NestedValue. */
            interface INestedValue {

                /** NestedValue nestedType */
                nestedType?: (perfetto.protos.DebugAnnotation.NestedValue.NestedType|null);

                /** NestedValue dictKeys */
                dictKeys?: (string[]|null);

                /** NestedValue dictValues */
                dictValues?: (perfetto.protos.DebugAnnotation.INestedValue[]|null);

                /** NestedValue arrayValues */
                arrayValues?: (perfetto.protos.DebugAnnotation.INestedValue[]|null);

                /** NestedValue intValue */
                intValue?: (number|Long|null);

                /** NestedValue doubleValue */
                doubleValue?: (number|null);

                /** NestedValue boolValue */
                boolValue?: (boolean|null);

                /** NestedValue stringValue */
                stringValue?: (string|null);
            }

            /** Represents a NestedValue. */
            class NestedValue implements INestedValue {

                /**
                 * Constructs a new NestedValue.
                 * @param [properties] Properties to set
                 */
                constructor(properties?: perfetto.protos.DebugAnnotation.INestedValue);

                /** NestedValue nestedType. */
                public nestedType: perfetto.protos.DebugAnnotation.NestedValue.NestedType;

                /** NestedValue dictKeys. */
                public dictKeys: string[];

                /** NestedValue dictValues. */
                public dictValues: perfetto.protos.DebugAnnotation.INestedValue[];

                /** NestedValue arrayValues. */
                public arrayValues: perfetto.protos.DebugAnnotation.INestedValue[];

                /** NestedValue intValue. */
                public intValue: (number|Long);

                /** NestedValue doubleValue. */
                public doubleValue: number;

                /** NestedValue boolValue. */
                public boolValue: boolean;

                /** NestedValue stringValue. */
                public stringValue: string;

                /**
                 * Creates a new NestedValue instance using the specified properties.
                 * @param [properties] Properties to set
                 * @returns NestedValue instance
                 */
                public static create(properties?: perfetto.protos.DebugAnnotation.INestedValue): perfetto.protos.DebugAnnotation.NestedValue;

                /**
                 * Encodes the specified NestedValue message. Does not implicitly {@link perfetto.protos.DebugAnnotation.NestedValue.verify|verify} messages.
                 * @param message NestedValue message or plain object to encode
                 * @param [writer] Writer to encode to
                 * @returns Writer
                 */
                public static encode(message: perfetto.protos.DebugAnnotation.INestedValue, writer?: $protobuf.Writer): $protobuf.Writer;

                /**
                 * Encodes the specified NestedValue message, length delimited. Does not implicitly {@link perfetto.protos.DebugAnnotation.NestedValue.verify|verify} messages.
                 * @param message NestedValue message or plain object to encode
                 * @param [writer] Writer to encode to
                 * @returns Writer
                 */
                public static encodeDelimited(message: perfetto.protos.DebugAnnotation.INestedValue, writer?: $protobuf.Writer): $protobuf.Writer;

                /**
                 * Decodes a NestedValue message from the specified reader or buffer.
                 * @param reader Reader or buffer to decode from
                 * @param [length] Message length if known beforehand
                 * @returns NestedValue
                 * @throws {Error} If the payload is not a reader or valid buffer
                 * @throws {$protobuf.util.ProtocolError} If required fields are missing
                 */
                public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.DebugAnnotation.NestedValue;

                /**
                 * Decodes a NestedValue message from the specified reader or buffer, length delimited.
                 * @param reader Reader or buffer to decode from
                 * @returns NestedValue
                 * @throws {Error} If the payload is not a reader or valid buffer
                 * @throws {$protobuf.util.ProtocolError} If required fields are missing
                 */
                public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.DebugAnnotation.NestedValue;

                /**
                 * Verifies a NestedValue message.
                 * @param message Plain object to verify
                 * @returns `null` if valid, otherwise the reason why it is not
                 */
                public static verify(message: { [k: string]: any }): (string|null);

                /**
                 * Creates a NestedValue message from a plain object. Also converts values to their respective internal types.
                 * @param object Plain object
                 * @returns NestedValue
                 */
                public static fromObject(object: { [k: string]: any }): perfetto.protos.DebugAnnotation.NestedValue;

                /**
                 * Creates a plain object from a NestedValue message. Also converts values to other types if specified.
                 * @param message NestedValue
                 * @param [options] Conversion options
                 * @returns Plain object
                 */
                public static toObject(message: perfetto.protos.DebugAnnotation.NestedValue, options?: $protobuf.IConversionOptions): { [k: string]: any };

                /**
                 * Converts this NestedValue to JSON.
                 * @returns JSON object
                 */
                public toJSON(): { [k: string]: any };

                /**
                 * Gets the default type url for NestedValue
                 * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
                 * @returns The default type url
                 */
                public static getTypeUrl(typeUrlPrefix?: string): string;
            }

            namespace NestedValue {

                /** NestedType enum. */
                enum NestedType {
                    UNSPECIFIED = 0,
                    DICT = 1,
                    ARRAY = 2
                }
            }
        }

        /** Properties of an UnsymbolizedSourceLocation. */
        interface IUnsymbolizedSourceLocation {

            /** UnsymbolizedSourceLocation iid */
            iid?: (number|Long|null);

            /** UnsymbolizedSourceLocation mappingId */
            mappingId?: (number|Long|null);

            /** UnsymbolizedSourceLocation relPc */
            relPc?: (number|Long|null);
        }

        /** Represents an UnsymbolizedSourceLocation. */
        class UnsymbolizedSourceLocation implements IUnsymbolizedSourceLocation {

            /**
             * Constructs a new UnsymbolizedSourceLocation.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.IUnsymbolizedSourceLocation);

            /** UnsymbolizedSourceLocation iid. */
            public iid: (number|Long);

            /** UnsymbolizedSourceLocation mappingId. */
            public mappingId: (number|Long);

            /** UnsymbolizedSourceLocation relPc. */
            public relPc: (number|Long);

            /**
             * Creates a new UnsymbolizedSourceLocation instance using the specified properties.
             * @param [properties] Properties to set
             * @returns UnsymbolizedSourceLocation instance
             */
            public static create(properties?: perfetto.protos.IUnsymbolizedSourceLocation): perfetto.protos.UnsymbolizedSourceLocation;

            /**
             * Encodes the specified UnsymbolizedSourceLocation message. Does not implicitly {@link perfetto.protos.UnsymbolizedSourceLocation.verify|verify} messages.
             * @param message UnsymbolizedSourceLocation message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.IUnsymbolizedSourceLocation, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified UnsymbolizedSourceLocation message, length delimited. Does not implicitly {@link perfetto.protos.UnsymbolizedSourceLocation.verify|verify} messages.
             * @param message UnsymbolizedSourceLocation message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.IUnsymbolizedSourceLocation, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes an UnsymbolizedSourceLocation message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns UnsymbolizedSourceLocation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.UnsymbolizedSourceLocation;

            /**
             * Decodes an UnsymbolizedSourceLocation message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns UnsymbolizedSourceLocation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.UnsymbolizedSourceLocation;

            /**
             * Verifies an UnsymbolizedSourceLocation message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates an UnsymbolizedSourceLocation message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns UnsymbolizedSourceLocation
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.UnsymbolizedSourceLocation;

            /**
             * Creates a plain object from an UnsymbolizedSourceLocation message. Also converts values to other types if specified.
             * @param message UnsymbolizedSourceLocation
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.UnsymbolizedSourceLocation, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this UnsymbolizedSourceLocation to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for UnsymbolizedSourceLocation
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        /** Properties of a SourceLocation. */
        interface ISourceLocation {

            /** SourceLocation iid */
            iid?: (number|Long|null);

            /** SourceLocation fileName */
            fileName?: (string|null);

            /** SourceLocation functionName */
            functionName?: (string|null);

            /** SourceLocation lineNumber */
            lineNumber?: (number|null);
        }

        /** Represents a SourceLocation. */
        class SourceLocation implements ISourceLocation {

            /**
             * Constructs a new SourceLocation.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.ISourceLocation);

            /** SourceLocation iid. */
            public iid: (number|Long);

            /** SourceLocation fileName. */
            public fileName: string;

            /** SourceLocation functionName. */
            public functionName: string;

            /** SourceLocation lineNumber. */
            public lineNumber: number;

            /**
             * Creates a new SourceLocation instance using the specified properties.
             * @param [properties] Properties to set
             * @returns SourceLocation instance
             */
            public static create(properties?: perfetto.protos.ISourceLocation): perfetto.protos.SourceLocation;

            /**
             * Encodes the specified SourceLocation message. Does not implicitly {@link perfetto.protos.SourceLocation.verify|verify} messages.
             * @param message SourceLocation message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.ISourceLocation, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified SourceLocation message, length delimited. Does not implicitly {@link perfetto.protos.SourceLocation.verify|verify} messages.
             * @param message SourceLocation message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.ISourceLocation, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a SourceLocation message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns SourceLocation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.SourceLocation;

            /**
             * Decodes a SourceLocation message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns SourceLocation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.SourceLocation;

            /**
             * Verifies a SourceLocation message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a SourceLocation message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns SourceLocation
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.SourceLocation;

            /**
             * Creates a plain object from a SourceLocation message. Also converts values to other types if specified.
             * @param message SourceLocation
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.SourceLocation, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this SourceLocation to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for SourceLocation
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        /** Properties of a ProcessDescriptor. */
        interface IProcessDescriptor {

            /** ProcessDescriptor pid */
            pid?: (number|null);

            /** ProcessDescriptor cmdline */
            cmdline?: (string[]|null);

            /** ProcessDescriptor processName */
            processName?: (string|null);

            /** ProcessDescriptor processPriority */
            processPriority?: (number|null);

            /** ProcessDescriptor startTimestampNs */
            startTimestampNs?: (number|Long|null);

            /** ProcessDescriptor chromeProcessType */
            chromeProcessType?: (perfetto.protos.ProcessDescriptor.ChromeProcessType|null);

            /** ProcessDescriptor legacySortIndex */
            legacySortIndex?: (number|null);

            /** ProcessDescriptor processLabels */
            processLabels?: (string[]|null);
        }

        /** Represents a ProcessDescriptor. */
        class ProcessDescriptor implements IProcessDescriptor {

            /**
             * Constructs a new ProcessDescriptor.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.IProcessDescriptor);

            /** ProcessDescriptor pid. */
            public pid: number;

            /** ProcessDescriptor cmdline. */
            public cmdline: string[];

            /** ProcessDescriptor processName. */
            public processName: string;

            /** ProcessDescriptor processPriority. */
            public processPriority: number;

            /** ProcessDescriptor startTimestampNs. */
            public startTimestampNs: (number|Long);

            /** ProcessDescriptor chromeProcessType. */
            public chromeProcessType: perfetto.protos.ProcessDescriptor.ChromeProcessType;

            /** ProcessDescriptor legacySortIndex. */
            public legacySortIndex: number;

            /** ProcessDescriptor processLabels. */
            public processLabels: string[];

            /**
             * Creates a new ProcessDescriptor instance using the specified properties.
             * @param [properties] Properties to set
             * @returns ProcessDescriptor instance
             */
            public static create(properties?: perfetto.protos.IProcessDescriptor): perfetto.protos.ProcessDescriptor;

            /**
             * Encodes the specified ProcessDescriptor message. Does not implicitly {@link perfetto.protos.ProcessDescriptor.verify|verify} messages.
             * @param message ProcessDescriptor message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.IProcessDescriptor, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified ProcessDescriptor message, length delimited. Does not implicitly {@link perfetto.protos.ProcessDescriptor.verify|verify} messages.
             * @param message ProcessDescriptor message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.IProcessDescriptor, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a ProcessDescriptor message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns ProcessDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.ProcessDescriptor;

            /**
             * Decodes a ProcessDescriptor message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns ProcessDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.ProcessDescriptor;

            /**
             * Verifies a ProcessDescriptor message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a ProcessDescriptor message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns ProcessDescriptor
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.ProcessDescriptor;

            /**
             * Creates a plain object from a ProcessDescriptor message. Also converts values to other types if specified.
             * @param message ProcessDescriptor
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.ProcessDescriptor, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this ProcessDescriptor to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for ProcessDescriptor
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        namespace ProcessDescriptor {

            /** ChromeProcessType enum. */
            enum ChromeProcessType {
                PROCESS_UNSPECIFIED = 0,
                PROCESS_BROWSER = 1,
                PROCESS_RENDERER = 2,
                PROCESS_UTILITY = 3,
                PROCESS_ZYGOTE = 4,
                PROCESS_SANDBOX_HELPER = 5,
                PROCESS_GPU = 6,
                PROCESS_PPAPI_PLUGIN = 7,
                PROCESS_PPAPI_BROKER = 8
            }
        }

        /** Properties of a ThreadDescriptor. */
        interface IThreadDescriptor {

            /** ThreadDescriptor pid */
            pid?: (number|null);

            /** ThreadDescriptor tid */
            tid?: (number|null);

            /** ThreadDescriptor threadName */
            threadName?: (string|null);

            /** ThreadDescriptor chromeThreadType */
            chromeThreadType?: (perfetto.protos.ThreadDescriptor.ChromeThreadType|null);

            /** ThreadDescriptor referenceTimestampUs */
            referenceTimestampUs?: (number|Long|null);

            /** ThreadDescriptor referenceThreadTimeUs */
            referenceThreadTimeUs?: (number|Long|null);

            /** ThreadDescriptor referenceThreadInstructionCount */
            referenceThreadInstructionCount?: (number|Long|null);

            /** ThreadDescriptor legacySortIndex */
            legacySortIndex?: (number|null);
        }

        /** Represents a ThreadDescriptor. */
        class ThreadDescriptor implements IThreadDescriptor {

            /**
             * Constructs a new ThreadDescriptor.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.IThreadDescriptor);

            /** ThreadDescriptor pid. */
            public pid: number;

            /** ThreadDescriptor tid. */
            public tid: number;

            /** ThreadDescriptor threadName. */
            public threadName: string;

            /** ThreadDescriptor chromeThreadType. */
            public chromeThreadType: perfetto.protos.ThreadDescriptor.ChromeThreadType;

            /** ThreadDescriptor referenceTimestampUs. */
            public referenceTimestampUs: (number|Long);

            /** ThreadDescriptor referenceThreadTimeUs. */
            public referenceThreadTimeUs: (number|Long);

            /** ThreadDescriptor referenceThreadInstructionCount. */
            public referenceThreadInstructionCount: (number|Long);

            /** ThreadDescriptor legacySortIndex. */
            public legacySortIndex: number;

            /**
             * Creates a new ThreadDescriptor instance using the specified properties.
             * @param [properties] Properties to set
             * @returns ThreadDescriptor instance
             */
            public static create(properties?: perfetto.protos.IThreadDescriptor): perfetto.protos.ThreadDescriptor;

            /**
             * Encodes the specified ThreadDescriptor message. Does not implicitly {@link perfetto.protos.ThreadDescriptor.verify|verify} messages.
             * @param message ThreadDescriptor message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.IThreadDescriptor, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified ThreadDescriptor message, length delimited. Does not implicitly {@link perfetto.protos.ThreadDescriptor.verify|verify} messages.
             * @param message ThreadDescriptor message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.IThreadDescriptor, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a ThreadDescriptor message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns ThreadDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.ThreadDescriptor;

            /**
             * Decodes a ThreadDescriptor message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns ThreadDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.ThreadDescriptor;

            /**
             * Verifies a ThreadDescriptor message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a ThreadDescriptor message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns ThreadDescriptor
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.ThreadDescriptor;

            /**
             * Creates a plain object from a ThreadDescriptor message. Also converts values to other types if specified.
             * @param message ThreadDescriptor
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.ThreadDescriptor, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this ThreadDescriptor to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for ThreadDescriptor
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        namespace ThreadDescriptor {

            /** ChromeThreadType enum. */
            enum ChromeThreadType {
                CHROME_THREAD_UNSPECIFIED = 0,
                CHROME_THREAD_MAIN = 1,
                CHROME_THREAD_IO = 2,
                CHROME_THREAD_POOL_BG_WORKER = 3,
                CHROME_THREAD_POOL_FG_WORKER = 4,
                CHROME_THREAD_POOL_FB_BLOCKING = 5,
                CHROME_THREAD_POOL_BG_BLOCKING = 6,
                CHROME_THREAD_POOL_SERVICE = 7,
                CHROME_THREAD_COMPOSITOR = 8,
                CHROME_THREAD_VIZ_COMPOSITOR = 9,
                CHROME_THREAD_COMPOSITOR_WORKER = 10,
                CHROME_THREAD_SERVICE_WORKER = 11,
                CHROME_THREAD_MEMORY_INFRA = 50,
                CHROME_THREAD_SAMPLING_PROFILER = 51
            }
        }

        /** Properties of a TrackDescriptor. */
        interface ITrackDescriptor {

            /** TrackDescriptor uuid */
            uuid?: (number|Long|null);

            /** TrackDescriptor parentUuid */
            parentUuid?: (number|Long|null);

            /** TrackDescriptor name */
            name?: (string|null);

            /** TrackDescriptor process */
            process?: (perfetto.protos.IProcessDescriptor|null);

            /** TrackDescriptor thread */
            thread?: (perfetto.protos.IThreadDescriptor|null);
        }

        /** Represents a TrackDescriptor. */
        class TrackDescriptor implements ITrackDescriptor {

            /**
             * Constructs a new TrackDescriptor.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.ITrackDescriptor);

            /** TrackDescriptor uuid. */
            public uuid: (number|Long);

            /** TrackDescriptor parentUuid. */
            public parentUuid: (number|Long);

            /** TrackDescriptor name. */
            public name: string;

            /** TrackDescriptor process. */
            public process?: (perfetto.protos.IProcessDescriptor|null);

            /** TrackDescriptor thread. */
            public thread?: (perfetto.protos.IThreadDescriptor|null);

            /**
             * Creates a new TrackDescriptor instance using the specified properties.
             * @param [properties] Properties to set
             * @returns TrackDescriptor instance
             */
            public static create(properties?: perfetto.protos.ITrackDescriptor): perfetto.protos.TrackDescriptor;

            /**
             * Encodes the specified TrackDescriptor message. Does not implicitly {@link perfetto.protos.TrackDescriptor.verify|verify} messages.
             * @param message TrackDescriptor message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.ITrackDescriptor, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified TrackDescriptor message, length delimited. Does not implicitly {@link perfetto.protos.TrackDescriptor.verify|verify} messages.
             * @param message TrackDescriptor message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.ITrackDescriptor, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a TrackDescriptor message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns TrackDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.TrackDescriptor;

            /**
             * Decodes a TrackDescriptor message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns TrackDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.TrackDescriptor;

            /**
             * Verifies a TrackDescriptor message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a TrackDescriptor message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns TrackDescriptor
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.TrackDescriptor;

            /**
             * Creates a plain object from a TrackDescriptor message. Also converts values to other types if specified.
             * @param message TrackDescriptor
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.TrackDescriptor, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this TrackDescriptor to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for TrackDescriptor
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        /** Properties of a TrackEvent. */
        interface ITrackEvent {

            /** TrackEvent categoryIids */
            categoryIids?: ((number|Long)[]|null);

            /** TrackEvent categories */
            categories?: (string[]|null);

            /** TrackEvent nameIid */
            nameIid?: (number|Long|null);

            /** TrackEvent name */
            name?: (string|null);

            /** TrackEvent type */
            type?: (perfetto.protos.TrackEvent.Type|null);

            /** TrackEvent trackUuid */
            trackUuid?: (number|Long|null);

            /** TrackEvent counterValue */
            counterValue?: (number|Long|null);

            /** TrackEvent doubleCounterValue */
            doubleCounterValue?: (number|null);

            /** TrackEvent extraCounterTrackUuids */
            extraCounterTrackUuids?: ((number|Long)[]|null);

            /** TrackEvent extraCounterValues */
            extraCounterValues?: ((number|Long)[]|null);

            /** TrackEvent extraDoubleCounterTrackUuids */
            extraDoubleCounterTrackUuids?: ((number|Long)[]|null);

            /** TrackEvent extraDoubleCounterValues */
            extraDoubleCounterValues?: (number[]|null);

            /** TrackEvent flowIdsOld */
            flowIdsOld?: ((number|Long)[]|null);

            /** TrackEvent flowIds */
            flowIds?: ((number|Long)[]|null);

            /** TrackEvent terminatingFlowIdsOld */
            terminatingFlowIdsOld?: ((number|Long)[]|null);

            /** TrackEvent terminatingFlowIds */
            terminatingFlowIds?: ((number|Long)[]|null);

            /** TrackEvent debugAnnotations */
            debugAnnotations?: (perfetto.protos.IDebugAnnotation[]|null);

            /** TrackEvent sourceLocation */
            sourceLocation?: (perfetto.protos.ISourceLocation|null);

            /** TrackEvent sourceLocationIid */
            sourceLocationIid?: (number|Long|null);
        }

        /** Represents a TrackEvent. */
        class TrackEvent implements ITrackEvent {

            /**
             * Constructs a new TrackEvent.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.ITrackEvent);

            /** TrackEvent categoryIids. */
            public categoryIids: (number|Long)[];

            /** TrackEvent categories. */
            public categories: string[];

            /** TrackEvent nameIid. */
            public nameIid?: (number|Long|null);

            /** TrackEvent name. */
            public name?: (string|null);

            /** TrackEvent type. */
            public type: perfetto.protos.TrackEvent.Type;

            /** TrackEvent trackUuid. */
            public trackUuid: (number|Long);

            /** TrackEvent counterValue. */
            public counterValue?: (number|Long|null);

            /** TrackEvent doubleCounterValue. */
            public doubleCounterValue?: (number|null);

            /** TrackEvent extraCounterTrackUuids. */
            public extraCounterTrackUuids: (number|Long)[];

            /** TrackEvent extraCounterValues. */
            public extraCounterValues: (number|Long)[];

            /** TrackEvent extraDoubleCounterTrackUuids. */
            public extraDoubleCounterTrackUuids: (number|Long)[];

            /** TrackEvent extraDoubleCounterValues. */
            public extraDoubleCounterValues: number[];

            /** TrackEvent flowIdsOld. */
            public flowIdsOld: (number|Long)[];

            /** TrackEvent flowIds. */
            public flowIds: (number|Long)[];

            /** TrackEvent terminatingFlowIdsOld. */
            public terminatingFlowIdsOld: (number|Long)[];

            /** TrackEvent terminatingFlowIds. */
            public terminatingFlowIds: (number|Long)[];

            /** TrackEvent debugAnnotations. */
            public debugAnnotations: perfetto.protos.IDebugAnnotation[];

            /** TrackEvent sourceLocation. */
            public sourceLocation?: (perfetto.protos.ISourceLocation|null);

            /** TrackEvent sourceLocationIid. */
            public sourceLocationIid?: (number|Long|null);

            /** TrackEvent nameField. */
            public nameField?: ("nameIid"|"name");

            /** TrackEvent counterValueField. */
            public counterValueField?: ("counterValue"|"doubleCounterValue");

            /** TrackEvent sourceLocationField. */
            public sourceLocationField?: ("sourceLocation"|"sourceLocationIid");

            /**
             * Creates a new TrackEvent instance using the specified properties.
             * @param [properties] Properties to set
             * @returns TrackEvent instance
             */
            public static create(properties?: perfetto.protos.ITrackEvent): perfetto.protos.TrackEvent;

            /**
             * Encodes the specified TrackEvent message. Does not implicitly {@link perfetto.protos.TrackEvent.verify|verify} messages.
             * @param message TrackEvent message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.ITrackEvent, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified TrackEvent message, length delimited. Does not implicitly {@link perfetto.protos.TrackEvent.verify|verify} messages.
             * @param message TrackEvent message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.ITrackEvent, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a TrackEvent message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns TrackEvent
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.TrackEvent;

            /**
             * Decodes a TrackEvent message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns TrackEvent
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.TrackEvent;

            /**
             * Verifies a TrackEvent message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a TrackEvent message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns TrackEvent
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.TrackEvent;

            /**
             * Creates a plain object from a TrackEvent message. Also converts values to other types if specified.
             * @param message TrackEvent
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.TrackEvent, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this TrackEvent to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for TrackEvent
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        namespace TrackEvent {

            /** Type enum. */
            enum Type {
                TYPE_UNSPECIFIED = 0,
                TYPE_SLICE_BEGIN = 1,
                TYPE_SLICE_END = 2,
                TYPE_INSTANT = 3,
                TYPE_COUNTER = 4
            }
        }

        /** Properties of a TracePacket. */
        interface ITracePacket {

            /** TracePacket timestamp */
            timestamp?: (number|Long|null);

            /** TracePacket timestampClockId */
            timestampClockId?: (number|null);

            /** TracePacket trackEvent */
            trackEvent?: (perfetto.protos.ITrackEvent|null);

            /** TracePacket trackDescriptor */
            trackDescriptor?: (perfetto.protos.ITrackDescriptor|null);

            /** TracePacket internedData */
            internedData?: (perfetto.protos.IInternedData|null);

            /** TracePacket sequenceFlags */
            sequenceFlags?: (number|null);

            /** TracePacket trustedUid */
            trustedUid?: (number|null);

            /** TracePacket trustedPacketSequenceId */
            trustedPacketSequenceId?: (number|null);

            /** TracePacket trustedPid */
            trustedPid?: (number|null);

            /** TracePacket previousPacketDropped */
            previousPacketDropped?: (boolean|null);

            /** TracePacket firstPacketOnSequence */
            firstPacketOnSequence?: (boolean|null);
        }

        /** Represents a TracePacket. */
        class TracePacket implements ITracePacket {

            /**
             * Constructs a new TracePacket.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.ITracePacket);

            /** TracePacket timestamp. */
            public timestamp: (number|Long);

            /** TracePacket timestampClockId. */
            public timestampClockId: number;

            /** TracePacket trackEvent. */
            public trackEvent?: (perfetto.protos.ITrackEvent|null);

            /** TracePacket trackDescriptor. */
            public trackDescriptor?: (perfetto.protos.ITrackDescriptor|null);

            /** TracePacket internedData. */
            public internedData?: (perfetto.protos.IInternedData|null);

            /** TracePacket sequenceFlags. */
            public sequenceFlags: number;

            /** TracePacket trustedUid. */
            public trustedUid?: (number|null);

            /** TracePacket trustedPacketSequenceId. */
            public trustedPacketSequenceId?: (number|null);

            /** TracePacket trustedPid. */
            public trustedPid: number;

            /** TracePacket previousPacketDropped. */
            public previousPacketDropped: boolean;

            /** TracePacket firstPacketOnSequence. */
            public firstPacketOnSequence: boolean;

            /** TracePacket data. */
            public data?: ("trackEvent"|"trackDescriptor");

            /** TracePacket optionalTrustedUid. */
            public optionalTrustedUid?: "trustedUid";

            /** TracePacket optionalTrustedPacketSequenceId. */
            public optionalTrustedPacketSequenceId?: "trustedPacketSequenceId";

            /**
             * Creates a new TracePacket instance using the specified properties.
             * @param [properties] Properties to set
             * @returns TracePacket instance
             */
            public static create(properties?: perfetto.protos.ITracePacket): perfetto.protos.TracePacket;

            /**
             * Encodes the specified TracePacket message. Does not implicitly {@link perfetto.protos.TracePacket.verify|verify} messages.
             * @param message TracePacket message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.ITracePacket, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified TracePacket message, length delimited. Does not implicitly {@link perfetto.protos.TracePacket.verify|verify} messages.
             * @param message TracePacket message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.ITracePacket, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a TracePacket message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns TracePacket
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.TracePacket;

            /**
             * Decodes a TracePacket message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns TracePacket
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.TracePacket;

            /**
             * Verifies a TracePacket message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a TracePacket message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns TracePacket
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.TracePacket;

            /**
             * Creates a plain object from a TracePacket message. Also converts values to other types if specified.
             * @param message TracePacket
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.TracePacket, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this TracePacket to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for TracePacket
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }

        namespace TracePacket {

            /** SequenceFlags enum. */
            enum SequenceFlags {
                SEQ_UNSPECIFIED = 0,
                SEQ_INCREMENTAL_STATE_CLEARED = 1,
                SEQ_NEEDS_INCREMENTAL_STATE = 2
            }
        }

        /** Properties of a Trace. */
        interface ITrace {

            /** Trace packet */
            packet?: (perfetto.protos.ITracePacket[]|null);
        }

        /** Represents a Trace. */
        class Trace implements ITrace {

            /**
             * Constructs a new Trace.
             * @param [properties] Properties to set
             */
            constructor(properties?: perfetto.protos.ITrace);

            /** Trace packet. */
            public packet: perfetto.protos.ITracePacket[];

            /**
             * Creates a new Trace instance using the specified properties.
             * @param [properties] Properties to set
             * @returns Trace instance
             */
            public static create(properties?: perfetto.protos.ITrace): perfetto.protos.Trace;

            /**
             * Encodes the specified Trace message. Does not implicitly {@link perfetto.protos.Trace.verify|verify} messages.
             * @param message Trace message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encode(message: perfetto.protos.ITrace, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Encodes the specified Trace message, length delimited. Does not implicitly {@link perfetto.protos.Trace.verify|verify} messages.
             * @param message Trace message or plain object to encode
             * @param [writer] Writer to encode to
             * @returns Writer
             */
            public static encodeDelimited(message: perfetto.protos.ITrace, writer?: $protobuf.Writer): $protobuf.Writer;

            /**
             * Decodes a Trace message from the specified reader or buffer.
             * @param reader Reader or buffer to decode from
             * @param [length] Message length if known beforehand
             * @returns Trace
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decode(reader: ($protobuf.Reader|Uint8Array), length?: number): perfetto.protos.Trace;

            /**
             * Decodes a Trace message from the specified reader or buffer, length delimited.
             * @param reader Reader or buffer to decode from
             * @returns Trace
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            public static decodeDelimited(reader: ($protobuf.Reader|Uint8Array)): perfetto.protos.Trace;

            /**
             * Verifies a Trace message.
             * @param message Plain object to verify
             * @returns `null` if valid, otherwise the reason why it is not
             */
            public static verify(message: { [k: string]: any }): (string|null);

            /**
             * Creates a Trace message from a plain object. Also converts values to their respective internal types.
             * @param object Plain object
             * @returns Trace
             */
            public static fromObject(object: { [k: string]: any }): perfetto.protos.Trace;

            /**
             * Creates a plain object from a Trace message. Also converts values to other types if specified.
             * @param message Trace
             * @param [options] Conversion options
             * @returns Plain object
             */
            public static toObject(message: perfetto.protos.Trace, options?: $protobuf.IConversionOptions): { [k: string]: any };

            /**
             * Converts this Trace to JSON.
             * @returns JSON object
             */
            public toJSON(): { [k: string]: any };

            /**
             * Gets the default type url for Trace
             * @param [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns The default type url
             */
            public static getTypeUrl(typeUrlPrefix?: string): string;
        }
    }
}
