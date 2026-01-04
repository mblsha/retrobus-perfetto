/*eslint-disable block-scoped-var, id-length, no-control-regex, no-magic-numbers, no-prototype-builtins, no-redeclare, no-shadow, no-var, sort-vars*/
import * as $protobuf from "protobufjs/minimal";

// Common aliases
const $Reader = $protobuf.Reader, $Writer = $protobuf.Writer, $util = $protobuf.util;

// Exported root namespace
const $root = $protobuf.roots["default"] || ($protobuf.roots["default"] = {});

export const perfetto = $root.perfetto = (() => {

    /**
     * Namespace perfetto.
     * @exports perfetto
     * @namespace
     */
    const perfetto = {};

    perfetto.protos = (function() {

        /**
         * Namespace protos.
         * @memberof perfetto
         * @namespace
         */
        const protos = {};

        protos.EventName = (function() {

            /**
             * Properties of an EventName.
             * @memberof perfetto.protos
             * @interface IEventName
             * @property {number|Long|null} [iid] EventName iid
             * @property {string|null} [name] EventName name
             */

            /**
             * Constructs a new EventName.
             * @memberof perfetto.protos
             * @classdesc Represents an EventName.
             * @implements IEventName
             * @constructor
             * @param {perfetto.protos.IEventName=} [properties] Properties to set
             */
            function EventName(properties) {
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * EventName iid.
             * @member {number|Long} iid
             * @memberof perfetto.protos.EventName
             * @instance
             */
            EventName.prototype.iid = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * EventName name.
             * @member {string} name
             * @memberof perfetto.protos.EventName
             * @instance
             */
            EventName.prototype.name = "";

            /**
             * Creates a new EventName instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.EventName
             * @static
             * @param {perfetto.protos.IEventName=} [properties] Properties to set
             * @returns {perfetto.protos.EventName} EventName instance
             */
            EventName.create = function create(properties) {
                return new EventName(properties);
            };

            /**
             * Encodes the specified EventName message. Does not implicitly {@link perfetto.protos.EventName.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.EventName
             * @static
             * @param {perfetto.protos.IEventName} message EventName message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            EventName.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.iid != null && Object.hasOwnProperty.call(message, "iid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).uint64(message.iid);
                if (message.name != null && Object.hasOwnProperty.call(message, "name"))
                    writer.uint32(/* id 2, wireType 2 =*/18).string(message.name);
                return writer;
            };

            /**
             * Encodes the specified EventName message, length delimited. Does not implicitly {@link perfetto.protos.EventName.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.EventName
             * @static
             * @param {perfetto.protos.IEventName} message EventName message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            EventName.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes an EventName message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.EventName
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.EventName} EventName
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            EventName.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.EventName();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.iid = reader.uint64();
                            break;
                        }
                    case 2: {
                            message.name = reader.string();
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes an EventName message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.EventName
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.EventName} EventName
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            EventName.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies an EventName message.
             * @function verify
             * @memberof perfetto.protos.EventName
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            EventName.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (!$util.isInteger(message.iid) && !(message.iid && $util.isInteger(message.iid.low) && $util.isInteger(message.iid.high)))
                        return "iid: integer|Long expected";
                if (message.name != null && message.hasOwnProperty("name"))
                    if (!$util.isString(message.name))
                        return "name: string expected";
                return null;
            };

            /**
             * Creates an EventName message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.EventName
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.EventName} EventName
             */
            EventName.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.EventName)
                    return object;
                let message = new $root.perfetto.protos.EventName();
                if (object.iid != null)
                    if ($util.Long)
                        (message.iid = $util.Long.fromValue(object.iid)).unsigned = true;
                    else if (typeof object.iid === "string")
                        message.iid = parseInt(object.iid, 10);
                    else if (typeof object.iid === "number")
                        message.iid = object.iid;
                    else if (typeof object.iid === "object")
                        message.iid = new $util.LongBits(object.iid.low >>> 0, object.iid.high >>> 0).toNumber(true);
                if (object.name != null)
                    message.name = String(object.name);
                return message;
            };

            /**
             * Creates a plain object from an EventName message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.EventName
             * @static
             * @param {perfetto.protos.EventName} message EventName
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            EventName.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.defaults) {
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.iid = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.iid = options.longs === String ? "0" : 0;
                    object.name = "";
                }
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (typeof message.iid === "number")
                        object.iid = options.longs === String ? String(message.iid) : message.iid;
                    else
                        object.iid = options.longs === String ? $util.Long.prototype.toString.call(message.iid) : options.longs === Number ? new $util.LongBits(message.iid.low >>> 0, message.iid.high >>> 0).toNumber(true) : message.iid;
                if (message.name != null && message.hasOwnProperty("name"))
                    object.name = message.name;
                return object;
            };

            /**
             * Converts this EventName to JSON.
             * @function toJSON
             * @memberof perfetto.protos.EventName
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            EventName.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for EventName
             * @function getTypeUrl
             * @memberof perfetto.protos.EventName
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            EventName.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.EventName";
            };

            return EventName;
        })();

        protos.DebugAnnotationName = (function() {

            /**
             * Properties of a DebugAnnotationName.
             * @memberof perfetto.protos
             * @interface IDebugAnnotationName
             * @property {number|Long|null} [iid] DebugAnnotationName iid
             * @property {string|null} [name] DebugAnnotationName name
             */

            /**
             * Constructs a new DebugAnnotationName.
             * @memberof perfetto.protos
             * @classdesc Represents a DebugAnnotationName.
             * @implements IDebugAnnotationName
             * @constructor
             * @param {perfetto.protos.IDebugAnnotationName=} [properties] Properties to set
             */
            function DebugAnnotationName(properties) {
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * DebugAnnotationName iid.
             * @member {number|Long} iid
             * @memberof perfetto.protos.DebugAnnotationName
             * @instance
             */
            DebugAnnotationName.prototype.iid = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * DebugAnnotationName name.
             * @member {string} name
             * @memberof perfetto.protos.DebugAnnotationName
             * @instance
             */
            DebugAnnotationName.prototype.name = "";

            /**
             * Creates a new DebugAnnotationName instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {perfetto.protos.IDebugAnnotationName=} [properties] Properties to set
             * @returns {perfetto.protos.DebugAnnotationName} DebugAnnotationName instance
             */
            DebugAnnotationName.create = function create(properties) {
                return new DebugAnnotationName(properties);
            };

            /**
             * Encodes the specified DebugAnnotationName message. Does not implicitly {@link perfetto.protos.DebugAnnotationName.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {perfetto.protos.IDebugAnnotationName} message DebugAnnotationName message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            DebugAnnotationName.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.iid != null && Object.hasOwnProperty.call(message, "iid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).uint64(message.iid);
                if (message.name != null && Object.hasOwnProperty.call(message, "name"))
                    writer.uint32(/* id 2, wireType 2 =*/18).string(message.name);
                return writer;
            };

            /**
             * Encodes the specified DebugAnnotationName message, length delimited. Does not implicitly {@link perfetto.protos.DebugAnnotationName.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {perfetto.protos.IDebugAnnotationName} message DebugAnnotationName message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            DebugAnnotationName.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a DebugAnnotationName message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.DebugAnnotationName} DebugAnnotationName
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            DebugAnnotationName.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.DebugAnnotationName();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.iid = reader.uint64();
                            break;
                        }
                    case 2: {
                            message.name = reader.string();
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a DebugAnnotationName message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.DebugAnnotationName} DebugAnnotationName
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            DebugAnnotationName.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a DebugAnnotationName message.
             * @function verify
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            DebugAnnotationName.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (!$util.isInteger(message.iid) && !(message.iid && $util.isInteger(message.iid.low) && $util.isInteger(message.iid.high)))
                        return "iid: integer|Long expected";
                if (message.name != null && message.hasOwnProperty("name"))
                    if (!$util.isString(message.name))
                        return "name: string expected";
                return null;
            };

            /**
             * Creates a DebugAnnotationName message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.DebugAnnotationName} DebugAnnotationName
             */
            DebugAnnotationName.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.DebugAnnotationName)
                    return object;
                let message = new $root.perfetto.protos.DebugAnnotationName();
                if (object.iid != null)
                    if ($util.Long)
                        (message.iid = $util.Long.fromValue(object.iid)).unsigned = true;
                    else if (typeof object.iid === "string")
                        message.iid = parseInt(object.iid, 10);
                    else if (typeof object.iid === "number")
                        message.iid = object.iid;
                    else if (typeof object.iid === "object")
                        message.iid = new $util.LongBits(object.iid.low >>> 0, object.iid.high >>> 0).toNumber(true);
                if (object.name != null)
                    message.name = String(object.name);
                return message;
            };

            /**
             * Creates a plain object from a DebugAnnotationName message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {perfetto.protos.DebugAnnotationName} message DebugAnnotationName
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            DebugAnnotationName.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.defaults) {
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.iid = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.iid = options.longs === String ? "0" : 0;
                    object.name = "";
                }
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (typeof message.iid === "number")
                        object.iid = options.longs === String ? String(message.iid) : message.iid;
                    else
                        object.iid = options.longs === String ? $util.Long.prototype.toString.call(message.iid) : options.longs === Number ? new $util.LongBits(message.iid.low >>> 0, message.iid.high >>> 0).toNumber(true) : message.iid;
                if (message.name != null && message.hasOwnProperty("name"))
                    object.name = message.name;
                return object;
            };

            /**
             * Converts this DebugAnnotationName to JSON.
             * @function toJSON
             * @memberof perfetto.protos.DebugAnnotationName
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            DebugAnnotationName.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for DebugAnnotationName
             * @function getTypeUrl
             * @memberof perfetto.protos.DebugAnnotationName
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            DebugAnnotationName.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.DebugAnnotationName";
            };

            return DebugAnnotationName;
        })();

        protos.InternedString = (function() {

            /**
             * Properties of an InternedString.
             * @memberof perfetto.protos
             * @interface IInternedString
             * @property {number|Long|null} [iid] InternedString iid
             * @property {Uint8Array|null} [str] InternedString str
             */

            /**
             * Constructs a new InternedString.
             * @memberof perfetto.protos
             * @classdesc Represents an InternedString.
             * @implements IInternedString
             * @constructor
             * @param {perfetto.protos.IInternedString=} [properties] Properties to set
             */
            function InternedString(properties) {
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * InternedString iid.
             * @member {number|Long} iid
             * @memberof perfetto.protos.InternedString
             * @instance
             */
            InternedString.prototype.iid = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * InternedString str.
             * @member {Uint8Array} str
             * @memberof perfetto.protos.InternedString
             * @instance
             */
            InternedString.prototype.str = $util.newBuffer([]);

            /**
             * Creates a new InternedString instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {perfetto.protos.IInternedString=} [properties] Properties to set
             * @returns {perfetto.protos.InternedString} InternedString instance
             */
            InternedString.create = function create(properties) {
                return new InternedString(properties);
            };

            /**
             * Encodes the specified InternedString message. Does not implicitly {@link perfetto.protos.InternedString.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {perfetto.protos.IInternedString} message InternedString message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            InternedString.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.iid != null && Object.hasOwnProperty.call(message, "iid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).uint64(message.iid);
                if (message.str != null && Object.hasOwnProperty.call(message, "str"))
                    writer.uint32(/* id 2, wireType 2 =*/18).bytes(message.str);
                return writer;
            };

            /**
             * Encodes the specified InternedString message, length delimited. Does not implicitly {@link perfetto.protos.InternedString.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {perfetto.protos.IInternedString} message InternedString message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            InternedString.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes an InternedString message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.InternedString} InternedString
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            InternedString.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.InternedString();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.iid = reader.uint64();
                            break;
                        }
                    case 2: {
                            message.str = reader.bytes();
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes an InternedString message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.InternedString} InternedString
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            InternedString.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies an InternedString message.
             * @function verify
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            InternedString.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (!$util.isInteger(message.iid) && !(message.iid && $util.isInteger(message.iid.low) && $util.isInteger(message.iid.high)))
                        return "iid: integer|Long expected";
                if (message.str != null && message.hasOwnProperty("str"))
                    if (!(message.str && typeof message.str.length === "number" || $util.isString(message.str)))
                        return "str: buffer expected";
                return null;
            };

            /**
             * Creates an InternedString message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.InternedString} InternedString
             */
            InternedString.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.InternedString)
                    return object;
                let message = new $root.perfetto.protos.InternedString();
                if (object.iid != null)
                    if ($util.Long)
                        (message.iid = $util.Long.fromValue(object.iid)).unsigned = true;
                    else if (typeof object.iid === "string")
                        message.iid = parseInt(object.iid, 10);
                    else if (typeof object.iid === "number")
                        message.iid = object.iid;
                    else if (typeof object.iid === "object")
                        message.iid = new $util.LongBits(object.iid.low >>> 0, object.iid.high >>> 0).toNumber(true);
                if (object.str != null)
                    if (typeof object.str === "string")
                        $util.base64.decode(object.str, message.str = $util.newBuffer($util.base64.length(object.str)), 0);
                    else if (object.str.length >= 0)
                        message.str = object.str;
                return message;
            };

            /**
             * Creates a plain object from an InternedString message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {perfetto.protos.InternedString} message InternedString
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            InternedString.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.defaults) {
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.iid = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.iid = options.longs === String ? "0" : 0;
                    if (options.bytes === String)
                        object.str = "";
                    else {
                        object.str = [];
                        if (options.bytes !== Array)
                            object.str = $util.newBuffer(object.str);
                    }
                }
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (typeof message.iid === "number")
                        object.iid = options.longs === String ? String(message.iid) : message.iid;
                    else
                        object.iid = options.longs === String ? $util.Long.prototype.toString.call(message.iid) : options.longs === Number ? new $util.LongBits(message.iid.low >>> 0, message.iid.high >>> 0).toNumber(true) : message.iid;
                if (message.str != null && message.hasOwnProperty("str"))
                    object.str = options.bytes === String ? $util.base64.encode(message.str, 0, message.str.length) : options.bytes === Array ? Array.prototype.slice.call(message.str) : message.str;
                return object;
            };

            /**
             * Converts this InternedString to JSON.
             * @function toJSON
             * @memberof perfetto.protos.InternedString
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            InternedString.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for InternedString
             * @function getTypeUrl
             * @memberof perfetto.protos.InternedString
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            InternedString.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.InternedString";
            };

            return InternedString;
        })();

        protos.InternedData = (function() {

            /**
             * Properties of an InternedData.
             * @memberof perfetto.protos
             * @interface IInternedData
             * @property {Array.<perfetto.protos.IEventName>|null} [eventNames] InternedData eventNames
             * @property {Array.<perfetto.protos.IDebugAnnotationName>|null} [debugAnnotationNames] InternedData debugAnnotationNames
             * @property {Array.<perfetto.protos.IInternedString>|null} [debugAnnotationStringValues] InternedData debugAnnotationStringValues
             */

            /**
             * Constructs a new InternedData.
             * @memberof perfetto.protos
             * @classdesc Represents an InternedData.
             * @implements IInternedData
             * @constructor
             * @param {perfetto.protos.IInternedData=} [properties] Properties to set
             */
            function InternedData(properties) {
                this.eventNames = [];
                this.debugAnnotationNames = [];
                this.debugAnnotationStringValues = [];
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * InternedData eventNames.
             * @member {Array.<perfetto.protos.IEventName>} eventNames
             * @memberof perfetto.protos.InternedData
             * @instance
             */
            InternedData.prototype.eventNames = $util.emptyArray;

            /**
             * InternedData debugAnnotationNames.
             * @member {Array.<perfetto.protos.IDebugAnnotationName>} debugAnnotationNames
             * @memberof perfetto.protos.InternedData
             * @instance
             */
            InternedData.prototype.debugAnnotationNames = $util.emptyArray;

            /**
             * InternedData debugAnnotationStringValues.
             * @member {Array.<perfetto.protos.IInternedString>} debugAnnotationStringValues
             * @memberof perfetto.protos.InternedData
             * @instance
             */
            InternedData.prototype.debugAnnotationStringValues = $util.emptyArray;

            /**
             * Creates a new InternedData instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {perfetto.protos.IInternedData=} [properties] Properties to set
             * @returns {perfetto.protos.InternedData} InternedData instance
             */
            InternedData.create = function create(properties) {
                return new InternedData(properties);
            };

            /**
             * Encodes the specified InternedData message. Does not implicitly {@link perfetto.protos.InternedData.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {perfetto.protos.IInternedData} message InternedData message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            InternedData.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.eventNames != null && message.eventNames.length)
                    for (let i = 0; i < message.eventNames.length; ++i)
                        $root.perfetto.protos.EventName.encode(message.eventNames[i], writer.uint32(/* id 2, wireType 2 =*/18).fork()).ldelim();
                if (message.debugAnnotationNames != null && message.debugAnnotationNames.length)
                    for (let i = 0; i < message.debugAnnotationNames.length; ++i)
                        $root.perfetto.protos.DebugAnnotationName.encode(message.debugAnnotationNames[i], writer.uint32(/* id 3, wireType 2 =*/26).fork()).ldelim();
                if (message.debugAnnotationStringValues != null && message.debugAnnotationStringValues.length)
                    for (let i = 0; i < message.debugAnnotationStringValues.length; ++i)
                        $root.perfetto.protos.InternedString.encode(message.debugAnnotationStringValues[i], writer.uint32(/* id 29, wireType 2 =*/234).fork()).ldelim();
                return writer;
            };

            /**
             * Encodes the specified InternedData message, length delimited. Does not implicitly {@link perfetto.protos.InternedData.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {perfetto.protos.IInternedData} message InternedData message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            InternedData.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes an InternedData message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.InternedData} InternedData
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            InternedData.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.InternedData();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 2: {
                            if (!(message.eventNames && message.eventNames.length))
                                message.eventNames = [];
                            message.eventNames.push($root.perfetto.protos.EventName.decode(reader, reader.uint32()));
                            break;
                        }
                    case 3: {
                            if (!(message.debugAnnotationNames && message.debugAnnotationNames.length))
                                message.debugAnnotationNames = [];
                            message.debugAnnotationNames.push($root.perfetto.protos.DebugAnnotationName.decode(reader, reader.uint32()));
                            break;
                        }
                    case 29: {
                            if (!(message.debugAnnotationStringValues && message.debugAnnotationStringValues.length))
                                message.debugAnnotationStringValues = [];
                            message.debugAnnotationStringValues.push($root.perfetto.protos.InternedString.decode(reader, reader.uint32()));
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes an InternedData message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.InternedData} InternedData
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            InternedData.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies an InternedData message.
             * @function verify
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            InternedData.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.eventNames != null && message.hasOwnProperty("eventNames")) {
                    if (!Array.isArray(message.eventNames))
                        return "eventNames: array expected";
                    for (let i = 0; i < message.eventNames.length; ++i) {
                        let error = $root.perfetto.protos.EventName.verify(message.eventNames[i]);
                        if (error)
                            return "eventNames." + error;
                    }
                }
                if (message.debugAnnotationNames != null && message.hasOwnProperty("debugAnnotationNames")) {
                    if (!Array.isArray(message.debugAnnotationNames))
                        return "debugAnnotationNames: array expected";
                    for (let i = 0; i < message.debugAnnotationNames.length; ++i) {
                        let error = $root.perfetto.protos.DebugAnnotationName.verify(message.debugAnnotationNames[i]);
                        if (error)
                            return "debugAnnotationNames." + error;
                    }
                }
                if (message.debugAnnotationStringValues != null && message.hasOwnProperty("debugAnnotationStringValues")) {
                    if (!Array.isArray(message.debugAnnotationStringValues))
                        return "debugAnnotationStringValues: array expected";
                    for (let i = 0; i < message.debugAnnotationStringValues.length; ++i) {
                        let error = $root.perfetto.protos.InternedString.verify(message.debugAnnotationStringValues[i]);
                        if (error)
                            return "debugAnnotationStringValues." + error;
                    }
                }
                return null;
            };

            /**
             * Creates an InternedData message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.InternedData} InternedData
             */
            InternedData.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.InternedData)
                    return object;
                let message = new $root.perfetto.protos.InternedData();
                if (object.eventNames) {
                    if (!Array.isArray(object.eventNames))
                        throw TypeError(".perfetto.protos.InternedData.eventNames: array expected");
                    message.eventNames = [];
                    for (let i = 0; i < object.eventNames.length; ++i) {
                        if (typeof object.eventNames[i] !== "object")
                            throw TypeError(".perfetto.protos.InternedData.eventNames: object expected");
                        message.eventNames[i] = $root.perfetto.protos.EventName.fromObject(object.eventNames[i]);
                    }
                }
                if (object.debugAnnotationNames) {
                    if (!Array.isArray(object.debugAnnotationNames))
                        throw TypeError(".perfetto.protos.InternedData.debugAnnotationNames: array expected");
                    message.debugAnnotationNames = [];
                    for (let i = 0; i < object.debugAnnotationNames.length; ++i) {
                        if (typeof object.debugAnnotationNames[i] !== "object")
                            throw TypeError(".perfetto.protos.InternedData.debugAnnotationNames: object expected");
                        message.debugAnnotationNames[i] = $root.perfetto.protos.DebugAnnotationName.fromObject(object.debugAnnotationNames[i]);
                    }
                }
                if (object.debugAnnotationStringValues) {
                    if (!Array.isArray(object.debugAnnotationStringValues))
                        throw TypeError(".perfetto.protos.InternedData.debugAnnotationStringValues: array expected");
                    message.debugAnnotationStringValues = [];
                    for (let i = 0; i < object.debugAnnotationStringValues.length; ++i) {
                        if (typeof object.debugAnnotationStringValues[i] !== "object")
                            throw TypeError(".perfetto.protos.InternedData.debugAnnotationStringValues: object expected");
                        message.debugAnnotationStringValues[i] = $root.perfetto.protos.InternedString.fromObject(object.debugAnnotationStringValues[i]);
                    }
                }
                return message;
            };

            /**
             * Creates a plain object from an InternedData message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {perfetto.protos.InternedData} message InternedData
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            InternedData.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.arrays || options.defaults) {
                    object.eventNames = [];
                    object.debugAnnotationNames = [];
                    object.debugAnnotationStringValues = [];
                }
                if (message.eventNames && message.eventNames.length) {
                    object.eventNames = [];
                    for (let j = 0; j < message.eventNames.length; ++j)
                        object.eventNames[j] = $root.perfetto.protos.EventName.toObject(message.eventNames[j], options);
                }
                if (message.debugAnnotationNames && message.debugAnnotationNames.length) {
                    object.debugAnnotationNames = [];
                    for (let j = 0; j < message.debugAnnotationNames.length; ++j)
                        object.debugAnnotationNames[j] = $root.perfetto.protos.DebugAnnotationName.toObject(message.debugAnnotationNames[j], options);
                }
                if (message.debugAnnotationStringValues && message.debugAnnotationStringValues.length) {
                    object.debugAnnotationStringValues = [];
                    for (let j = 0; j < message.debugAnnotationStringValues.length; ++j)
                        object.debugAnnotationStringValues[j] = $root.perfetto.protos.InternedString.toObject(message.debugAnnotationStringValues[j], options);
                }
                return object;
            };

            /**
             * Converts this InternedData to JSON.
             * @function toJSON
             * @memberof perfetto.protos.InternedData
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            InternedData.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for InternedData
             * @function getTypeUrl
             * @memberof perfetto.protos.InternedData
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            InternedData.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.InternedData";
            };

            return InternedData;
        })();

        protos.DebugAnnotation = (function() {

            /**
             * Properties of a DebugAnnotation.
             * @memberof perfetto.protos
             * @interface IDebugAnnotation
             * @property {number|Long|null} [nameIid] DebugAnnotation nameIid
             * @property {string|null} [name] DebugAnnotation name
             * @property {boolean|null} [boolValue] DebugAnnotation boolValue
             * @property {number|Long|null} [uintValue] DebugAnnotation uintValue
             * @property {number|Long|null} [intValue] DebugAnnotation intValue
             * @property {number|null} [doubleValue] DebugAnnotation doubleValue
             * @property {number|Long|null} [pointerValue] DebugAnnotation pointerValue
             * @property {perfetto.protos.DebugAnnotation.INestedValue|null} [nestedValue] DebugAnnotation nestedValue
             * @property {string|null} [legacyJsonValue] DebugAnnotation legacyJsonValue
             * @property {string|null} [stringValue] DebugAnnotation stringValue
             * @property {number|Long|null} [stringValueIid] DebugAnnotation stringValueIid
             * @property {string|null} [protoTypeName] DebugAnnotation protoTypeName
             * @property {number|Long|null} [protoTypeNameIid] DebugAnnotation protoTypeNameIid
             * @property {Uint8Array|null} [protoValue] DebugAnnotation protoValue
             * @property {Array.<perfetto.protos.IDebugAnnotation>|null} [dictEntries] DebugAnnotation dictEntries
             * @property {Array.<perfetto.protos.IDebugAnnotation>|null} [arrayValues] DebugAnnotation arrayValues
             */

            /**
             * Constructs a new DebugAnnotation.
             * @memberof perfetto.protos
             * @classdesc Represents a DebugAnnotation.
             * @implements IDebugAnnotation
             * @constructor
             * @param {perfetto.protos.IDebugAnnotation=} [properties] Properties to set
             */
            function DebugAnnotation(properties) {
                this.dictEntries = [];
                this.arrayValues = [];
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * DebugAnnotation nameIid.
             * @member {number|Long|null|undefined} nameIid
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.nameIid = null;

            /**
             * DebugAnnotation name.
             * @member {string|null|undefined} name
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.name = null;

            /**
             * DebugAnnotation boolValue.
             * @member {boolean|null|undefined} boolValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.boolValue = null;

            /**
             * DebugAnnotation uintValue.
             * @member {number|Long|null|undefined} uintValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.uintValue = null;

            /**
             * DebugAnnotation intValue.
             * @member {number|Long|null|undefined} intValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.intValue = null;

            /**
             * DebugAnnotation doubleValue.
             * @member {number|null|undefined} doubleValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.doubleValue = null;

            /**
             * DebugAnnotation pointerValue.
             * @member {number|Long|null|undefined} pointerValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.pointerValue = null;

            /**
             * DebugAnnotation nestedValue.
             * @member {perfetto.protos.DebugAnnotation.INestedValue|null|undefined} nestedValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.nestedValue = null;

            /**
             * DebugAnnotation legacyJsonValue.
             * @member {string|null|undefined} legacyJsonValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.legacyJsonValue = null;

            /**
             * DebugAnnotation stringValue.
             * @member {string|null|undefined} stringValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.stringValue = null;

            /**
             * DebugAnnotation stringValueIid.
             * @member {number|Long|null|undefined} stringValueIid
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.stringValueIid = null;

            /**
             * DebugAnnotation protoTypeName.
             * @member {string|null|undefined} protoTypeName
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.protoTypeName = null;

            /**
             * DebugAnnotation protoTypeNameIid.
             * @member {number|Long|null|undefined} protoTypeNameIid
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.protoTypeNameIid = null;

            /**
             * DebugAnnotation protoValue.
             * @member {Uint8Array} protoValue
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.protoValue = $util.newBuffer([]);

            /**
             * DebugAnnotation dictEntries.
             * @member {Array.<perfetto.protos.IDebugAnnotation>} dictEntries
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.dictEntries = $util.emptyArray;

            /**
             * DebugAnnotation arrayValues.
             * @member {Array.<perfetto.protos.IDebugAnnotation>} arrayValues
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            DebugAnnotation.prototype.arrayValues = $util.emptyArray;

            // OneOf field names bound to virtual getters and setters
            let $oneOfFields;

            /**
             * DebugAnnotation nameField.
             * @member {"nameIid"|"name"|undefined} nameField
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            Object.defineProperty(DebugAnnotation.prototype, "nameField", {
                get: $util.oneOfGetter($oneOfFields = ["nameIid", "name"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * DebugAnnotation value.
             * @member {"boolValue"|"uintValue"|"intValue"|"doubleValue"|"pointerValue"|"nestedValue"|"legacyJsonValue"|"stringValue"|"stringValueIid"|undefined} value
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            Object.defineProperty(DebugAnnotation.prototype, "value", {
                get: $util.oneOfGetter($oneOfFields = ["boolValue", "uintValue", "intValue", "doubleValue", "pointerValue", "nestedValue", "legacyJsonValue", "stringValue", "stringValueIid"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * DebugAnnotation protoTypeDescriptor.
             * @member {"protoTypeName"|"protoTypeNameIid"|undefined} protoTypeDescriptor
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             */
            Object.defineProperty(DebugAnnotation.prototype, "protoTypeDescriptor", {
                get: $util.oneOfGetter($oneOfFields = ["protoTypeName", "protoTypeNameIid"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * Creates a new DebugAnnotation instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {perfetto.protos.IDebugAnnotation=} [properties] Properties to set
             * @returns {perfetto.protos.DebugAnnotation} DebugAnnotation instance
             */
            DebugAnnotation.create = function create(properties) {
                return new DebugAnnotation(properties);
            };

            /**
             * Encodes the specified DebugAnnotation message. Does not implicitly {@link perfetto.protos.DebugAnnotation.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {perfetto.protos.IDebugAnnotation} message DebugAnnotation message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            DebugAnnotation.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.nameIid != null && Object.hasOwnProperty.call(message, "nameIid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).uint64(message.nameIid);
                if (message.boolValue != null && Object.hasOwnProperty.call(message, "boolValue"))
                    writer.uint32(/* id 2, wireType 0 =*/16).bool(message.boolValue);
                if (message.uintValue != null && Object.hasOwnProperty.call(message, "uintValue"))
                    writer.uint32(/* id 3, wireType 0 =*/24).uint64(message.uintValue);
                if (message.intValue != null && Object.hasOwnProperty.call(message, "intValue"))
                    writer.uint32(/* id 4, wireType 0 =*/32).int64(message.intValue);
                if (message.doubleValue != null && Object.hasOwnProperty.call(message, "doubleValue"))
                    writer.uint32(/* id 5, wireType 1 =*/41).double(message.doubleValue);
                if (message.stringValue != null && Object.hasOwnProperty.call(message, "stringValue"))
                    writer.uint32(/* id 6, wireType 2 =*/50).string(message.stringValue);
                if (message.pointerValue != null && Object.hasOwnProperty.call(message, "pointerValue"))
                    writer.uint32(/* id 7, wireType 0 =*/56).uint64(message.pointerValue);
                if (message.nestedValue != null && Object.hasOwnProperty.call(message, "nestedValue"))
                    $root.perfetto.protos.DebugAnnotation.NestedValue.encode(message.nestedValue, writer.uint32(/* id 8, wireType 2 =*/66).fork()).ldelim();
                if (message.legacyJsonValue != null && Object.hasOwnProperty.call(message, "legacyJsonValue"))
                    writer.uint32(/* id 9, wireType 2 =*/74).string(message.legacyJsonValue);
                if (message.name != null && Object.hasOwnProperty.call(message, "name"))
                    writer.uint32(/* id 10, wireType 2 =*/82).string(message.name);
                if (message.dictEntries != null && message.dictEntries.length)
                    for (let i = 0; i < message.dictEntries.length; ++i)
                        $root.perfetto.protos.DebugAnnotation.encode(message.dictEntries[i], writer.uint32(/* id 11, wireType 2 =*/90).fork()).ldelim();
                if (message.arrayValues != null && message.arrayValues.length)
                    for (let i = 0; i < message.arrayValues.length; ++i)
                        $root.perfetto.protos.DebugAnnotation.encode(message.arrayValues[i], writer.uint32(/* id 12, wireType 2 =*/98).fork()).ldelim();
                if (message.protoTypeNameIid != null && Object.hasOwnProperty.call(message, "protoTypeNameIid"))
                    writer.uint32(/* id 13, wireType 0 =*/104).uint64(message.protoTypeNameIid);
                if (message.protoValue != null && Object.hasOwnProperty.call(message, "protoValue"))
                    writer.uint32(/* id 14, wireType 2 =*/114).bytes(message.protoValue);
                if (message.protoTypeName != null && Object.hasOwnProperty.call(message, "protoTypeName"))
                    writer.uint32(/* id 16, wireType 2 =*/130).string(message.protoTypeName);
                if (message.stringValueIid != null && Object.hasOwnProperty.call(message, "stringValueIid"))
                    writer.uint32(/* id 17, wireType 0 =*/136).uint64(message.stringValueIid);
                return writer;
            };

            /**
             * Encodes the specified DebugAnnotation message, length delimited. Does not implicitly {@link perfetto.protos.DebugAnnotation.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {perfetto.protos.IDebugAnnotation} message DebugAnnotation message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            DebugAnnotation.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a DebugAnnotation message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.DebugAnnotation} DebugAnnotation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            DebugAnnotation.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.DebugAnnotation();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.nameIid = reader.uint64();
                            break;
                        }
                    case 10: {
                            message.name = reader.string();
                            break;
                        }
                    case 2: {
                            message.boolValue = reader.bool();
                            break;
                        }
                    case 3: {
                            message.uintValue = reader.uint64();
                            break;
                        }
                    case 4: {
                            message.intValue = reader.int64();
                            break;
                        }
                    case 5: {
                            message.doubleValue = reader.double();
                            break;
                        }
                    case 7: {
                            message.pointerValue = reader.uint64();
                            break;
                        }
                    case 8: {
                            message.nestedValue = $root.perfetto.protos.DebugAnnotation.NestedValue.decode(reader, reader.uint32());
                            break;
                        }
                    case 9: {
                            message.legacyJsonValue = reader.string();
                            break;
                        }
                    case 6: {
                            message.stringValue = reader.string();
                            break;
                        }
                    case 17: {
                            message.stringValueIid = reader.uint64();
                            break;
                        }
                    case 16: {
                            message.protoTypeName = reader.string();
                            break;
                        }
                    case 13: {
                            message.protoTypeNameIid = reader.uint64();
                            break;
                        }
                    case 14: {
                            message.protoValue = reader.bytes();
                            break;
                        }
                    case 11: {
                            if (!(message.dictEntries && message.dictEntries.length))
                                message.dictEntries = [];
                            message.dictEntries.push($root.perfetto.protos.DebugAnnotation.decode(reader, reader.uint32()));
                            break;
                        }
                    case 12: {
                            if (!(message.arrayValues && message.arrayValues.length))
                                message.arrayValues = [];
                            message.arrayValues.push($root.perfetto.protos.DebugAnnotation.decode(reader, reader.uint32()));
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a DebugAnnotation message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.DebugAnnotation} DebugAnnotation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            DebugAnnotation.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a DebugAnnotation message.
             * @function verify
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            DebugAnnotation.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                let properties = {};
                if (message.nameIid != null && message.hasOwnProperty("nameIid")) {
                    properties.nameField = 1;
                    if (!$util.isInteger(message.nameIid) && !(message.nameIid && $util.isInteger(message.nameIid.low) && $util.isInteger(message.nameIid.high)))
                        return "nameIid: integer|Long expected";
                }
                if (message.name != null && message.hasOwnProperty("name")) {
                    if (properties.nameField === 1)
                        return "nameField: multiple values";
                    properties.nameField = 1;
                    if (!$util.isString(message.name))
                        return "name: string expected";
                }
                if (message.boolValue != null && message.hasOwnProperty("boolValue")) {
                    properties.value = 1;
                    if (typeof message.boolValue !== "boolean")
                        return "boolValue: boolean expected";
                }
                if (message.uintValue != null && message.hasOwnProperty("uintValue")) {
                    if (properties.value === 1)
                        return "value: multiple values";
                    properties.value = 1;
                    if (!$util.isInteger(message.uintValue) && !(message.uintValue && $util.isInteger(message.uintValue.low) && $util.isInteger(message.uintValue.high)))
                        return "uintValue: integer|Long expected";
                }
                if (message.intValue != null && message.hasOwnProperty("intValue")) {
                    if (properties.value === 1)
                        return "value: multiple values";
                    properties.value = 1;
                    if (!$util.isInteger(message.intValue) && !(message.intValue && $util.isInteger(message.intValue.low) && $util.isInteger(message.intValue.high)))
                        return "intValue: integer|Long expected";
                }
                if (message.doubleValue != null && message.hasOwnProperty("doubleValue")) {
                    if (properties.value === 1)
                        return "value: multiple values";
                    properties.value = 1;
                    if (typeof message.doubleValue !== "number")
                        return "doubleValue: number expected";
                }
                if (message.pointerValue != null && message.hasOwnProperty("pointerValue")) {
                    if (properties.value === 1)
                        return "value: multiple values";
                    properties.value = 1;
                    if (!$util.isInteger(message.pointerValue) && !(message.pointerValue && $util.isInteger(message.pointerValue.low) && $util.isInteger(message.pointerValue.high)))
                        return "pointerValue: integer|Long expected";
                }
                if (message.nestedValue != null && message.hasOwnProperty("nestedValue")) {
                    if (properties.value === 1)
                        return "value: multiple values";
                    properties.value = 1;
                    {
                        let error = $root.perfetto.protos.DebugAnnotation.NestedValue.verify(message.nestedValue);
                        if (error)
                            return "nestedValue." + error;
                    }
                }
                if (message.legacyJsonValue != null && message.hasOwnProperty("legacyJsonValue")) {
                    if (properties.value === 1)
                        return "value: multiple values";
                    properties.value = 1;
                    if (!$util.isString(message.legacyJsonValue))
                        return "legacyJsonValue: string expected";
                }
                if (message.stringValue != null && message.hasOwnProperty("stringValue")) {
                    if (properties.value === 1)
                        return "value: multiple values";
                    properties.value = 1;
                    if (!$util.isString(message.stringValue))
                        return "stringValue: string expected";
                }
                if (message.stringValueIid != null && message.hasOwnProperty("stringValueIid")) {
                    if (properties.value === 1)
                        return "value: multiple values";
                    properties.value = 1;
                    if (!$util.isInteger(message.stringValueIid) && !(message.stringValueIid && $util.isInteger(message.stringValueIid.low) && $util.isInteger(message.stringValueIid.high)))
                        return "stringValueIid: integer|Long expected";
                }
                if (message.protoTypeName != null && message.hasOwnProperty("protoTypeName")) {
                    properties.protoTypeDescriptor = 1;
                    if (!$util.isString(message.protoTypeName))
                        return "protoTypeName: string expected";
                }
                if (message.protoTypeNameIid != null && message.hasOwnProperty("protoTypeNameIid")) {
                    if (properties.protoTypeDescriptor === 1)
                        return "protoTypeDescriptor: multiple values";
                    properties.protoTypeDescriptor = 1;
                    if (!$util.isInteger(message.protoTypeNameIid) && !(message.protoTypeNameIid && $util.isInteger(message.protoTypeNameIid.low) && $util.isInteger(message.protoTypeNameIid.high)))
                        return "protoTypeNameIid: integer|Long expected";
                }
                if (message.protoValue != null && message.hasOwnProperty("protoValue"))
                    if (!(message.protoValue && typeof message.protoValue.length === "number" || $util.isString(message.protoValue)))
                        return "protoValue: buffer expected";
                if (message.dictEntries != null && message.hasOwnProperty("dictEntries")) {
                    if (!Array.isArray(message.dictEntries))
                        return "dictEntries: array expected";
                    for (let i = 0; i < message.dictEntries.length; ++i) {
                        let error = $root.perfetto.protos.DebugAnnotation.verify(message.dictEntries[i]);
                        if (error)
                            return "dictEntries." + error;
                    }
                }
                if (message.arrayValues != null && message.hasOwnProperty("arrayValues")) {
                    if (!Array.isArray(message.arrayValues))
                        return "arrayValues: array expected";
                    for (let i = 0; i < message.arrayValues.length; ++i) {
                        let error = $root.perfetto.protos.DebugAnnotation.verify(message.arrayValues[i]);
                        if (error)
                            return "arrayValues." + error;
                    }
                }
                return null;
            };

            /**
             * Creates a DebugAnnotation message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.DebugAnnotation} DebugAnnotation
             */
            DebugAnnotation.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.DebugAnnotation)
                    return object;
                let message = new $root.perfetto.protos.DebugAnnotation();
                if (object.nameIid != null)
                    if ($util.Long)
                        (message.nameIid = $util.Long.fromValue(object.nameIid)).unsigned = true;
                    else if (typeof object.nameIid === "string")
                        message.nameIid = parseInt(object.nameIid, 10);
                    else if (typeof object.nameIid === "number")
                        message.nameIid = object.nameIid;
                    else if (typeof object.nameIid === "object")
                        message.nameIid = new $util.LongBits(object.nameIid.low >>> 0, object.nameIid.high >>> 0).toNumber(true);
                if (object.name != null)
                    message.name = String(object.name);
                if (object.boolValue != null)
                    message.boolValue = Boolean(object.boolValue);
                if (object.uintValue != null)
                    if ($util.Long)
                        (message.uintValue = $util.Long.fromValue(object.uintValue)).unsigned = true;
                    else if (typeof object.uintValue === "string")
                        message.uintValue = parseInt(object.uintValue, 10);
                    else if (typeof object.uintValue === "number")
                        message.uintValue = object.uintValue;
                    else if (typeof object.uintValue === "object")
                        message.uintValue = new $util.LongBits(object.uintValue.low >>> 0, object.uintValue.high >>> 0).toNumber(true);
                if (object.intValue != null)
                    if ($util.Long)
                        (message.intValue = $util.Long.fromValue(object.intValue)).unsigned = false;
                    else if (typeof object.intValue === "string")
                        message.intValue = parseInt(object.intValue, 10);
                    else if (typeof object.intValue === "number")
                        message.intValue = object.intValue;
                    else if (typeof object.intValue === "object")
                        message.intValue = new $util.LongBits(object.intValue.low >>> 0, object.intValue.high >>> 0).toNumber();
                if (object.doubleValue != null)
                    message.doubleValue = Number(object.doubleValue);
                if (object.pointerValue != null)
                    if ($util.Long)
                        (message.pointerValue = $util.Long.fromValue(object.pointerValue)).unsigned = true;
                    else if (typeof object.pointerValue === "string")
                        message.pointerValue = parseInt(object.pointerValue, 10);
                    else if (typeof object.pointerValue === "number")
                        message.pointerValue = object.pointerValue;
                    else if (typeof object.pointerValue === "object")
                        message.pointerValue = new $util.LongBits(object.pointerValue.low >>> 0, object.pointerValue.high >>> 0).toNumber(true);
                if (object.nestedValue != null) {
                    if (typeof object.nestedValue !== "object")
                        throw TypeError(".perfetto.protos.DebugAnnotation.nestedValue: object expected");
                    message.nestedValue = $root.perfetto.protos.DebugAnnotation.NestedValue.fromObject(object.nestedValue);
                }
                if (object.legacyJsonValue != null)
                    message.legacyJsonValue = String(object.legacyJsonValue);
                if (object.stringValue != null)
                    message.stringValue = String(object.stringValue);
                if (object.stringValueIid != null)
                    if ($util.Long)
                        (message.stringValueIid = $util.Long.fromValue(object.stringValueIid)).unsigned = true;
                    else if (typeof object.stringValueIid === "string")
                        message.stringValueIid = parseInt(object.stringValueIid, 10);
                    else if (typeof object.stringValueIid === "number")
                        message.stringValueIid = object.stringValueIid;
                    else if (typeof object.stringValueIid === "object")
                        message.stringValueIid = new $util.LongBits(object.stringValueIid.low >>> 0, object.stringValueIid.high >>> 0).toNumber(true);
                if (object.protoTypeName != null)
                    message.protoTypeName = String(object.protoTypeName);
                if (object.protoTypeNameIid != null)
                    if ($util.Long)
                        (message.protoTypeNameIid = $util.Long.fromValue(object.protoTypeNameIid)).unsigned = true;
                    else if (typeof object.protoTypeNameIid === "string")
                        message.protoTypeNameIid = parseInt(object.protoTypeNameIid, 10);
                    else if (typeof object.protoTypeNameIid === "number")
                        message.protoTypeNameIid = object.protoTypeNameIid;
                    else if (typeof object.protoTypeNameIid === "object")
                        message.protoTypeNameIid = new $util.LongBits(object.protoTypeNameIid.low >>> 0, object.protoTypeNameIid.high >>> 0).toNumber(true);
                if (object.protoValue != null)
                    if (typeof object.protoValue === "string")
                        $util.base64.decode(object.protoValue, message.protoValue = $util.newBuffer($util.base64.length(object.protoValue)), 0);
                    else if (object.protoValue.length >= 0)
                        message.protoValue = object.protoValue;
                if (object.dictEntries) {
                    if (!Array.isArray(object.dictEntries))
                        throw TypeError(".perfetto.protos.DebugAnnotation.dictEntries: array expected");
                    message.dictEntries = [];
                    for (let i = 0; i < object.dictEntries.length; ++i) {
                        if (typeof object.dictEntries[i] !== "object")
                            throw TypeError(".perfetto.protos.DebugAnnotation.dictEntries: object expected");
                        message.dictEntries[i] = $root.perfetto.protos.DebugAnnotation.fromObject(object.dictEntries[i]);
                    }
                }
                if (object.arrayValues) {
                    if (!Array.isArray(object.arrayValues))
                        throw TypeError(".perfetto.protos.DebugAnnotation.arrayValues: array expected");
                    message.arrayValues = [];
                    for (let i = 0; i < object.arrayValues.length; ++i) {
                        if (typeof object.arrayValues[i] !== "object")
                            throw TypeError(".perfetto.protos.DebugAnnotation.arrayValues: object expected");
                        message.arrayValues[i] = $root.perfetto.protos.DebugAnnotation.fromObject(object.arrayValues[i]);
                    }
                }
                return message;
            };

            /**
             * Creates a plain object from a DebugAnnotation message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {perfetto.protos.DebugAnnotation} message DebugAnnotation
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            DebugAnnotation.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.arrays || options.defaults) {
                    object.dictEntries = [];
                    object.arrayValues = [];
                }
                if (options.defaults)
                    if (options.bytes === String)
                        object.protoValue = "";
                    else {
                        object.protoValue = [];
                        if (options.bytes !== Array)
                            object.protoValue = $util.newBuffer(object.protoValue);
                    }
                if (message.nameIid != null && message.hasOwnProperty("nameIid")) {
                    if (typeof message.nameIid === "number")
                        object.nameIid = options.longs === String ? String(message.nameIid) : message.nameIid;
                    else
                        object.nameIid = options.longs === String ? $util.Long.prototype.toString.call(message.nameIid) : options.longs === Number ? new $util.LongBits(message.nameIid.low >>> 0, message.nameIid.high >>> 0).toNumber(true) : message.nameIid;
                    if (options.oneofs)
                        object.nameField = "nameIid";
                }
                if (message.boolValue != null && message.hasOwnProperty("boolValue")) {
                    object.boolValue = message.boolValue;
                    if (options.oneofs)
                        object.value = "boolValue";
                }
                if (message.uintValue != null && message.hasOwnProperty("uintValue")) {
                    if (typeof message.uintValue === "number")
                        object.uintValue = options.longs === String ? String(message.uintValue) : message.uintValue;
                    else
                        object.uintValue = options.longs === String ? $util.Long.prototype.toString.call(message.uintValue) : options.longs === Number ? new $util.LongBits(message.uintValue.low >>> 0, message.uintValue.high >>> 0).toNumber(true) : message.uintValue;
                    if (options.oneofs)
                        object.value = "uintValue";
                }
                if (message.intValue != null && message.hasOwnProperty("intValue")) {
                    if (typeof message.intValue === "number")
                        object.intValue = options.longs === String ? String(message.intValue) : message.intValue;
                    else
                        object.intValue = options.longs === String ? $util.Long.prototype.toString.call(message.intValue) : options.longs === Number ? new $util.LongBits(message.intValue.low >>> 0, message.intValue.high >>> 0).toNumber() : message.intValue;
                    if (options.oneofs)
                        object.value = "intValue";
                }
                if (message.doubleValue != null && message.hasOwnProperty("doubleValue")) {
                    object.doubleValue = options.json && !isFinite(message.doubleValue) ? String(message.doubleValue) : message.doubleValue;
                    if (options.oneofs)
                        object.value = "doubleValue";
                }
                if (message.stringValue != null && message.hasOwnProperty("stringValue")) {
                    object.stringValue = message.stringValue;
                    if (options.oneofs)
                        object.value = "stringValue";
                }
                if (message.pointerValue != null && message.hasOwnProperty("pointerValue")) {
                    if (typeof message.pointerValue === "number")
                        object.pointerValue = options.longs === String ? String(message.pointerValue) : message.pointerValue;
                    else
                        object.pointerValue = options.longs === String ? $util.Long.prototype.toString.call(message.pointerValue) : options.longs === Number ? new $util.LongBits(message.pointerValue.low >>> 0, message.pointerValue.high >>> 0).toNumber(true) : message.pointerValue;
                    if (options.oneofs)
                        object.value = "pointerValue";
                }
                if (message.nestedValue != null && message.hasOwnProperty("nestedValue")) {
                    object.nestedValue = $root.perfetto.protos.DebugAnnotation.NestedValue.toObject(message.nestedValue, options);
                    if (options.oneofs)
                        object.value = "nestedValue";
                }
                if (message.legacyJsonValue != null && message.hasOwnProperty("legacyJsonValue")) {
                    object.legacyJsonValue = message.legacyJsonValue;
                    if (options.oneofs)
                        object.value = "legacyJsonValue";
                }
                if (message.name != null && message.hasOwnProperty("name")) {
                    object.name = message.name;
                    if (options.oneofs)
                        object.nameField = "name";
                }
                if (message.dictEntries && message.dictEntries.length) {
                    object.dictEntries = [];
                    for (let j = 0; j < message.dictEntries.length; ++j)
                        object.dictEntries[j] = $root.perfetto.protos.DebugAnnotation.toObject(message.dictEntries[j], options);
                }
                if (message.arrayValues && message.arrayValues.length) {
                    object.arrayValues = [];
                    for (let j = 0; j < message.arrayValues.length; ++j)
                        object.arrayValues[j] = $root.perfetto.protos.DebugAnnotation.toObject(message.arrayValues[j], options);
                }
                if (message.protoTypeNameIid != null && message.hasOwnProperty("protoTypeNameIid")) {
                    if (typeof message.protoTypeNameIid === "number")
                        object.protoTypeNameIid = options.longs === String ? String(message.protoTypeNameIid) : message.protoTypeNameIid;
                    else
                        object.protoTypeNameIid = options.longs === String ? $util.Long.prototype.toString.call(message.protoTypeNameIid) : options.longs === Number ? new $util.LongBits(message.protoTypeNameIid.low >>> 0, message.protoTypeNameIid.high >>> 0).toNumber(true) : message.protoTypeNameIid;
                    if (options.oneofs)
                        object.protoTypeDescriptor = "protoTypeNameIid";
                }
                if (message.protoValue != null && message.hasOwnProperty("protoValue"))
                    object.protoValue = options.bytes === String ? $util.base64.encode(message.protoValue, 0, message.protoValue.length) : options.bytes === Array ? Array.prototype.slice.call(message.protoValue) : message.protoValue;
                if (message.protoTypeName != null && message.hasOwnProperty("protoTypeName")) {
                    object.protoTypeName = message.protoTypeName;
                    if (options.oneofs)
                        object.protoTypeDescriptor = "protoTypeName";
                }
                if (message.stringValueIid != null && message.hasOwnProperty("stringValueIid")) {
                    if (typeof message.stringValueIid === "number")
                        object.stringValueIid = options.longs === String ? String(message.stringValueIid) : message.stringValueIid;
                    else
                        object.stringValueIid = options.longs === String ? $util.Long.prototype.toString.call(message.stringValueIid) : options.longs === Number ? new $util.LongBits(message.stringValueIid.low >>> 0, message.stringValueIid.high >>> 0).toNumber(true) : message.stringValueIid;
                    if (options.oneofs)
                        object.value = "stringValueIid";
                }
                return object;
            };

            /**
             * Converts this DebugAnnotation to JSON.
             * @function toJSON
             * @memberof perfetto.protos.DebugAnnotation
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            DebugAnnotation.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for DebugAnnotation
             * @function getTypeUrl
             * @memberof perfetto.protos.DebugAnnotation
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            DebugAnnotation.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.DebugAnnotation";
            };

            DebugAnnotation.NestedValue = (function() {

                /**
                 * Properties of a NestedValue.
                 * @memberof perfetto.protos.DebugAnnotation
                 * @interface INestedValue
                 * @property {perfetto.protos.DebugAnnotation.NestedValue.NestedType|null} [nestedType] NestedValue nestedType
                 * @property {Array.<string>|null} [dictKeys] NestedValue dictKeys
                 * @property {Array.<perfetto.protos.DebugAnnotation.INestedValue>|null} [dictValues] NestedValue dictValues
                 * @property {Array.<perfetto.protos.DebugAnnotation.INestedValue>|null} [arrayValues] NestedValue arrayValues
                 * @property {number|Long|null} [intValue] NestedValue intValue
                 * @property {number|null} [doubleValue] NestedValue doubleValue
                 * @property {boolean|null} [boolValue] NestedValue boolValue
                 * @property {string|null} [stringValue] NestedValue stringValue
                 */

                /**
                 * Constructs a new NestedValue.
                 * @memberof perfetto.protos.DebugAnnotation
                 * @classdesc Represents a NestedValue.
                 * @implements INestedValue
                 * @constructor
                 * @param {perfetto.protos.DebugAnnotation.INestedValue=} [properties] Properties to set
                 */
                function NestedValue(properties) {
                    this.dictKeys = [];
                    this.dictValues = [];
                    this.arrayValues = [];
                    if (properties)
                        for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                            if (properties[keys[i]] != null)
                                this[keys[i]] = properties[keys[i]];
                }

                /**
                 * NestedValue nestedType.
                 * @member {perfetto.protos.DebugAnnotation.NestedValue.NestedType} nestedType
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 */
                NestedValue.prototype.nestedType = 0;

                /**
                 * NestedValue dictKeys.
                 * @member {Array.<string>} dictKeys
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 */
                NestedValue.prototype.dictKeys = $util.emptyArray;

                /**
                 * NestedValue dictValues.
                 * @member {Array.<perfetto.protos.DebugAnnotation.INestedValue>} dictValues
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 */
                NestedValue.prototype.dictValues = $util.emptyArray;

                /**
                 * NestedValue arrayValues.
                 * @member {Array.<perfetto.protos.DebugAnnotation.INestedValue>} arrayValues
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 */
                NestedValue.prototype.arrayValues = $util.emptyArray;

                /**
                 * NestedValue intValue.
                 * @member {number|Long} intValue
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 */
                NestedValue.prototype.intValue = $util.Long ? $util.Long.fromBits(0,0,false) : 0;

                /**
                 * NestedValue doubleValue.
                 * @member {number} doubleValue
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 */
                NestedValue.prototype.doubleValue = 0;

                /**
                 * NestedValue boolValue.
                 * @member {boolean} boolValue
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 */
                NestedValue.prototype.boolValue = false;

                /**
                 * NestedValue stringValue.
                 * @member {string} stringValue
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 */
                NestedValue.prototype.stringValue = "";

                /**
                 * Creates a new NestedValue instance using the specified properties.
                 * @function create
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {perfetto.protos.DebugAnnotation.INestedValue=} [properties] Properties to set
                 * @returns {perfetto.protos.DebugAnnotation.NestedValue} NestedValue instance
                 */
                NestedValue.create = function create(properties) {
                    return new NestedValue(properties);
                };

                /**
                 * Encodes the specified NestedValue message. Does not implicitly {@link perfetto.protos.DebugAnnotation.NestedValue.verify|verify} messages.
                 * @function encode
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {perfetto.protos.DebugAnnotation.INestedValue} message NestedValue message or plain object to encode
                 * @param {$protobuf.Writer} [writer] Writer to encode to
                 * @returns {$protobuf.Writer} Writer
                 */
                NestedValue.encode = function encode(message, writer) {
                    if (!writer)
                        writer = $Writer.create();
                    if (message.nestedType != null && Object.hasOwnProperty.call(message, "nestedType"))
                        writer.uint32(/* id 1, wireType 0 =*/8).int32(message.nestedType);
                    if (message.dictKeys != null && message.dictKeys.length)
                        for (let i = 0; i < message.dictKeys.length; ++i)
                            writer.uint32(/* id 2, wireType 2 =*/18).string(message.dictKeys[i]);
                    if (message.dictValues != null && message.dictValues.length)
                        for (let i = 0; i < message.dictValues.length; ++i)
                            $root.perfetto.protos.DebugAnnotation.NestedValue.encode(message.dictValues[i], writer.uint32(/* id 3, wireType 2 =*/26).fork()).ldelim();
                    if (message.arrayValues != null && message.arrayValues.length)
                        for (let i = 0; i < message.arrayValues.length; ++i)
                            $root.perfetto.protos.DebugAnnotation.NestedValue.encode(message.arrayValues[i], writer.uint32(/* id 4, wireType 2 =*/34).fork()).ldelim();
                    if (message.intValue != null && Object.hasOwnProperty.call(message, "intValue"))
                        writer.uint32(/* id 5, wireType 0 =*/40).int64(message.intValue);
                    if (message.doubleValue != null && Object.hasOwnProperty.call(message, "doubleValue"))
                        writer.uint32(/* id 6, wireType 1 =*/49).double(message.doubleValue);
                    if (message.boolValue != null && Object.hasOwnProperty.call(message, "boolValue"))
                        writer.uint32(/* id 7, wireType 0 =*/56).bool(message.boolValue);
                    if (message.stringValue != null && Object.hasOwnProperty.call(message, "stringValue"))
                        writer.uint32(/* id 8, wireType 2 =*/66).string(message.stringValue);
                    return writer;
                };

                /**
                 * Encodes the specified NestedValue message, length delimited. Does not implicitly {@link perfetto.protos.DebugAnnotation.NestedValue.verify|verify} messages.
                 * @function encodeDelimited
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {perfetto.protos.DebugAnnotation.INestedValue} message NestedValue message or plain object to encode
                 * @param {$protobuf.Writer} [writer] Writer to encode to
                 * @returns {$protobuf.Writer} Writer
                 */
                NestedValue.encodeDelimited = function encodeDelimited(message, writer) {
                    return this.encode(message, writer).ldelim();
                };

                /**
                 * Decodes a NestedValue message from the specified reader or buffer.
                 * @function decode
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
                 * @param {number} [length] Message length if known beforehand
                 * @returns {perfetto.protos.DebugAnnotation.NestedValue} NestedValue
                 * @throws {Error} If the payload is not a reader or valid buffer
                 * @throws {$protobuf.util.ProtocolError} If required fields are missing
                 */
                NestedValue.decode = function decode(reader, length, error) {
                    if (!(reader instanceof $Reader))
                        reader = $Reader.create(reader);
                    let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.DebugAnnotation.NestedValue();
                    while (reader.pos < end) {
                        let tag = reader.uint32();
                        if (tag === error)
                            break;
                        switch (tag >>> 3) {
                        case 1: {
                                message.nestedType = reader.int32();
                                break;
                            }
                        case 2: {
                                if (!(message.dictKeys && message.dictKeys.length))
                                    message.dictKeys = [];
                                message.dictKeys.push(reader.string());
                                break;
                            }
                        case 3: {
                                if (!(message.dictValues && message.dictValues.length))
                                    message.dictValues = [];
                                message.dictValues.push($root.perfetto.protos.DebugAnnotation.NestedValue.decode(reader, reader.uint32()));
                                break;
                            }
                        case 4: {
                                if (!(message.arrayValues && message.arrayValues.length))
                                    message.arrayValues = [];
                                message.arrayValues.push($root.perfetto.protos.DebugAnnotation.NestedValue.decode(reader, reader.uint32()));
                                break;
                            }
                        case 5: {
                                message.intValue = reader.int64();
                                break;
                            }
                        case 6: {
                                message.doubleValue = reader.double();
                                break;
                            }
                        case 7: {
                                message.boolValue = reader.bool();
                                break;
                            }
                        case 8: {
                                message.stringValue = reader.string();
                                break;
                            }
                        default:
                            reader.skipType(tag & 7);
                            break;
                        }
                    }
                    return message;
                };

                /**
                 * Decodes a NestedValue message from the specified reader or buffer, length delimited.
                 * @function decodeDelimited
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
                 * @returns {perfetto.protos.DebugAnnotation.NestedValue} NestedValue
                 * @throws {Error} If the payload is not a reader or valid buffer
                 * @throws {$protobuf.util.ProtocolError} If required fields are missing
                 */
                NestedValue.decodeDelimited = function decodeDelimited(reader) {
                    if (!(reader instanceof $Reader))
                        reader = new $Reader(reader);
                    return this.decode(reader, reader.uint32());
                };

                /**
                 * Verifies a NestedValue message.
                 * @function verify
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {Object.<string,*>} message Plain object to verify
                 * @returns {string|null} `null` if valid, otherwise the reason why it is not
                 */
                NestedValue.verify = function verify(message) {
                    if (typeof message !== "object" || message === null)
                        return "object expected";
                    if (message.nestedType != null && message.hasOwnProperty("nestedType"))
                        switch (message.nestedType) {
                        default:
                            return "nestedType: enum value expected";
                        case 0:
                        case 1:
                        case 2:
                            break;
                        }
                    if (message.dictKeys != null && message.hasOwnProperty("dictKeys")) {
                        if (!Array.isArray(message.dictKeys))
                            return "dictKeys: array expected";
                        for (let i = 0; i < message.dictKeys.length; ++i)
                            if (!$util.isString(message.dictKeys[i]))
                                return "dictKeys: string[] expected";
                    }
                    if (message.dictValues != null && message.hasOwnProperty("dictValues")) {
                        if (!Array.isArray(message.dictValues))
                            return "dictValues: array expected";
                        for (let i = 0; i < message.dictValues.length; ++i) {
                            let error = $root.perfetto.protos.DebugAnnotation.NestedValue.verify(message.dictValues[i]);
                            if (error)
                                return "dictValues." + error;
                        }
                    }
                    if (message.arrayValues != null && message.hasOwnProperty("arrayValues")) {
                        if (!Array.isArray(message.arrayValues))
                            return "arrayValues: array expected";
                        for (let i = 0; i < message.arrayValues.length; ++i) {
                            let error = $root.perfetto.protos.DebugAnnotation.NestedValue.verify(message.arrayValues[i]);
                            if (error)
                                return "arrayValues." + error;
                        }
                    }
                    if (message.intValue != null && message.hasOwnProperty("intValue"))
                        if (!$util.isInteger(message.intValue) && !(message.intValue && $util.isInteger(message.intValue.low) && $util.isInteger(message.intValue.high)))
                            return "intValue: integer|Long expected";
                    if (message.doubleValue != null && message.hasOwnProperty("doubleValue"))
                        if (typeof message.doubleValue !== "number")
                            return "doubleValue: number expected";
                    if (message.boolValue != null && message.hasOwnProperty("boolValue"))
                        if (typeof message.boolValue !== "boolean")
                            return "boolValue: boolean expected";
                    if (message.stringValue != null && message.hasOwnProperty("stringValue"))
                        if (!$util.isString(message.stringValue))
                            return "stringValue: string expected";
                    return null;
                };

                /**
                 * Creates a NestedValue message from a plain object. Also converts values to their respective internal types.
                 * @function fromObject
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {Object.<string,*>} object Plain object
                 * @returns {perfetto.protos.DebugAnnotation.NestedValue} NestedValue
                 */
                NestedValue.fromObject = function fromObject(object) {
                    if (object instanceof $root.perfetto.protos.DebugAnnotation.NestedValue)
                        return object;
                    let message = new $root.perfetto.protos.DebugAnnotation.NestedValue();
                    switch (object.nestedType) {
                    default:
                        if (typeof object.nestedType === "number") {
                            message.nestedType = object.nestedType;
                            break;
                        }
                        break;
                    case "UNSPECIFIED":
                    case 0:
                        message.nestedType = 0;
                        break;
                    case "DICT":
                    case 1:
                        message.nestedType = 1;
                        break;
                    case "ARRAY":
                    case 2:
                        message.nestedType = 2;
                        break;
                    }
                    if (object.dictKeys) {
                        if (!Array.isArray(object.dictKeys))
                            throw TypeError(".perfetto.protos.DebugAnnotation.NestedValue.dictKeys: array expected");
                        message.dictKeys = [];
                        for (let i = 0; i < object.dictKeys.length; ++i)
                            message.dictKeys[i] = String(object.dictKeys[i]);
                    }
                    if (object.dictValues) {
                        if (!Array.isArray(object.dictValues))
                            throw TypeError(".perfetto.protos.DebugAnnotation.NestedValue.dictValues: array expected");
                        message.dictValues = [];
                        for (let i = 0; i < object.dictValues.length; ++i) {
                            if (typeof object.dictValues[i] !== "object")
                                throw TypeError(".perfetto.protos.DebugAnnotation.NestedValue.dictValues: object expected");
                            message.dictValues[i] = $root.perfetto.protos.DebugAnnotation.NestedValue.fromObject(object.dictValues[i]);
                        }
                    }
                    if (object.arrayValues) {
                        if (!Array.isArray(object.arrayValues))
                            throw TypeError(".perfetto.protos.DebugAnnotation.NestedValue.arrayValues: array expected");
                        message.arrayValues = [];
                        for (let i = 0; i < object.arrayValues.length; ++i) {
                            if (typeof object.arrayValues[i] !== "object")
                                throw TypeError(".perfetto.protos.DebugAnnotation.NestedValue.arrayValues: object expected");
                            message.arrayValues[i] = $root.perfetto.protos.DebugAnnotation.NestedValue.fromObject(object.arrayValues[i]);
                        }
                    }
                    if (object.intValue != null)
                        if ($util.Long)
                            (message.intValue = $util.Long.fromValue(object.intValue)).unsigned = false;
                        else if (typeof object.intValue === "string")
                            message.intValue = parseInt(object.intValue, 10);
                        else if (typeof object.intValue === "number")
                            message.intValue = object.intValue;
                        else if (typeof object.intValue === "object")
                            message.intValue = new $util.LongBits(object.intValue.low >>> 0, object.intValue.high >>> 0).toNumber();
                    if (object.doubleValue != null)
                        message.doubleValue = Number(object.doubleValue);
                    if (object.boolValue != null)
                        message.boolValue = Boolean(object.boolValue);
                    if (object.stringValue != null)
                        message.stringValue = String(object.stringValue);
                    return message;
                };

                /**
                 * Creates a plain object from a NestedValue message. Also converts values to other types if specified.
                 * @function toObject
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {perfetto.protos.DebugAnnotation.NestedValue} message NestedValue
                 * @param {$protobuf.IConversionOptions} [options] Conversion options
                 * @returns {Object.<string,*>} Plain object
                 */
                NestedValue.toObject = function toObject(message, options) {
                    if (!options)
                        options = {};
                    let object = {};
                    if (options.arrays || options.defaults) {
                        object.dictKeys = [];
                        object.dictValues = [];
                        object.arrayValues = [];
                    }
                    if (options.defaults) {
                        object.nestedType = options.enums === String ? "UNSPECIFIED" : 0;
                        if ($util.Long) {
                            let long = new $util.Long(0, 0, false);
                            object.intValue = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                        } else
                            object.intValue = options.longs === String ? "0" : 0;
                        object.doubleValue = 0;
                        object.boolValue = false;
                        object.stringValue = "";
                    }
                    if (message.nestedType != null && message.hasOwnProperty("nestedType"))
                        object.nestedType = options.enums === String ? $root.perfetto.protos.DebugAnnotation.NestedValue.NestedType[message.nestedType] === undefined ? message.nestedType : $root.perfetto.protos.DebugAnnotation.NestedValue.NestedType[message.nestedType] : message.nestedType;
                    if (message.dictKeys && message.dictKeys.length) {
                        object.dictKeys = [];
                        for (let j = 0; j < message.dictKeys.length; ++j)
                            object.dictKeys[j] = message.dictKeys[j];
                    }
                    if (message.dictValues && message.dictValues.length) {
                        object.dictValues = [];
                        for (let j = 0; j < message.dictValues.length; ++j)
                            object.dictValues[j] = $root.perfetto.protos.DebugAnnotation.NestedValue.toObject(message.dictValues[j], options);
                    }
                    if (message.arrayValues && message.arrayValues.length) {
                        object.arrayValues = [];
                        for (let j = 0; j < message.arrayValues.length; ++j)
                            object.arrayValues[j] = $root.perfetto.protos.DebugAnnotation.NestedValue.toObject(message.arrayValues[j], options);
                    }
                    if (message.intValue != null && message.hasOwnProperty("intValue"))
                        if (typeof message.intValue === "number")
                            object.intValue = options.longs === String ? String(message.intValue) : message.intValue;
                        else
                            object.intValue = options.longs === String ? $util.Long.prototype.toString.call(message.intValue) : options.longs === Number ? new $util.LongBits(message.intValue.low >>> 0, message.intValue.high >>> 0).toNumber() : message.intValue;
                    if (message.doubleValue != null && message.hasOwnProperty("doubleValue"))
                        object.doubleValue = options.json && !isFinite(message.doubleValue) ? String(message.doubleValue) : message.doubleValue;
                    if (message.boolValue != null && message.hasOwnProperty("boolValue"))
                        object.boolValue = message.boolValue;
                    if (message.stringValue != null && message.hasOwnProperty("stringValue"))
                        object.stringValue = message.stringValue;
                    return object;
                };

                /**
                 * Converts this NestedValue to JSON.
                 * @function toJSON
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @instance
                 * @returns {Object.<string,*>} JSON object
                 */
                NestedValue.prototype.toJSON = function toJSON() {
                    return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
                };

                /**
                 * Gets the default type url for NestedValue
                 * @function getTypeUrl
                 * @memberof perfetto.protos.DebugAnnotation.NestedValue
                 * @static
                 * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
                 * @returns {string} The default type url
                 */
                NestedValue.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                    if (typeUrlPrefix === undefined) {
                        typeUrlPrefix = "type.googleapis.com";
                    }
                    return typeUrlPrefix + "/perfetto.protos.DebugAnnotation.NestedValue";
                };

                /**
                 * NestedType enum.
                 * @name perfetto.protos.DebugAnnotation.NestedValue.NestedType
                 * @enum {number}
                 * @property {number} UNSPECIFIED=0 UNSPECIFIED value
                 * @property {number} DICT=1 DICT value
                 * @property {number} ARRAY=2 ARRAY value
                 */
                NestedValue.NestedType = (function() {
                    const valuesById = {}, values = Object.create(valuesById);
                    values[valuesById[0] = "UNSPECIFIED"] = 0;
                    values[valuesById[1] = "DICT"] = 1;
                    values[valuesById[2] = "ARRAY"] = 2;
                    return values;
                })();

                return NestedValue;
            })();

            return DebugAnnotation;
        })();

        protos.UnsymbolizedSourceLocation = (function() {

            /**
             * Properties of an UnsymbolizedSourceLocation.
             * @memberof perfetto.protos
             * @interface IUnsymbolizedSourceLocation
             * @property {number|Long|null} [iid] UnsymbolizedSourceLocation iid
             * @property {number|Long|null} [mappingId] UnsymbolizedSourceLocation mappingId
             * @property {number|Long|null} [relPc] UnsymbolizedSourceLocation relPc
             */

            /**
             * Constructs a new UnsymbolizedSourceLocation.
             * @memberof perfetto.protos
             * @classdesc Represents an UnsymbolizedSourceLocation.
             * @implements IUnsymbolizedSourceLocation
             * @constructor
             * @param {perfetto.protos.IUnsymbolizedSourceLocation=} [properties] Properties to set
             */
            function UnsymbolizedSourceLocation(properties) {
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * UnsymbolizedSourceLocation iid.
             * @member {number|Long} iid
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @instance
             */
            UnsymbolizedSourceLocation.prototype.iid = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * UnsymbolizedSourceLocation mappingId.
             * @member {number|Long} mappingId
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @instance
             */
            UnsymbolizedSourceLocation.prototype.mappingId = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * UnsymbolizedSourceLocation relPc.
             * @member {number|Long} relPc
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @instance
             */
            UnsymbolizedSourceLocation.prototype.relPc = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * Creates a new UnsymbolizedSourceLocation instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {perfetto.protos.IUnsymbolizedSourceLocation=} [properties] Properties to set
             * @returns {perfetto.protos.UnsymbolizedSourceLocation} UnsymbolizedSourceLocation instance
             */
            UnsymbolizedSourceLocation.create = function create(properties) {
                return new UnsymbolizedSourceLocation(properties);
            };

            /**
             * Encodes the specified UnsymbolizedSourceLocation message. Does not implicitly {@link perfetto.protos.UnsymbolizedSourceLocation.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {perfetto.protos.IUnsymbolizedSourceLocation} message UnsymbolizedSourceLocation message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            UnsymbolizedSourceLocation.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.iid != null && Object.hasOwnProperty.call(message, "iid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).uint64(message.iid);
                if (message.mappingId != null && Object.hasOwnProperty.call(message, "mappingId"))
                    writer.uint32(/* id 2, wireType 0 =*/16).uint64(message.mappingId);
                if (message.relPc != null && Object.hasOwnProperty.call(message, "relPc"))
                    writer.uint32(/* id 3, wireType 0 =*/24).uint64(message.relPc);
                return writer;
            };

            /**
             * Encodes the specified UnsymbolizedSourceLocation message, length delimited. Does not implicitly {@link perfetto.protos.UnsymbolizedSourceLocation.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {perfetto.protos.IUnsymbolizedSourceLocation} message UnsymbolizedSourceLocation message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            UnsymbolizedSourceLocation.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes an UnsymbolizedSourceLocation message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.UnsymbolizedSourceLocation} UnsymbolizedSourceLocation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            UnsymbolizedSourceLocation.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.UnsymbolizedSourceLocation();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.iid = reader.uint64();
                            break;
                        }
                    case 2: {
                            message.mappingId = reader.uint64();
                            break;
                        }
                    case 3: {
                            message.relPc = reader.uint64();
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes an UnsymbolizedSourceLocation message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.UnsymbolizedSourceLocation} UnsymbolizedSourceLocation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            UnsymbolizedSourceLocation.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies an UnsymbolizedSourceLocation message.
             * @function verify
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            UnsymbolizedSourceLocation.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (!$util.isInteger(message.iid) && !(message.iid && $util.isInteger(message.iid.low) && $util.isInteger(message.iid.high)))
                        return "iid: integer|Long expected";
                if (message.mappingId != null && message.hasOwnProperty("mappingId"))
                    if (!$util.isInteger(message.mappingId) && !(message.mappingId && $util.isInteger(message.mappingId.low) && $util.isInteger(message.mappingId.high)))
                        return "mappingId: integer|Long expected";
                if (message.relPc != null && message.hasOwnProperty("relPc"))
                    if (!$util.isInteger(message.relPc) && !(message.relPc && $util.isInteger(message.relPc.low) && $util.isInteger(message.relPc.high)))
                        return "relPc: integer|Long expected";
                return null;
            };

            /**
             * Creates an UnsymbolizedSourceLocation message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.UnsymbolizedSourceLocation} UnsymbolizedSourceLocation
             */
            UnsymbolizedSourceLocation.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.UnsymbolizedSourceLocation)
                    return object;
                let message = new $root.perfetto.protos.UnsymbolizedSourceLocation();
                if (object.iid != null)
                    if ($util.Long)
                        (message.iid = $util.Long.fromValue(object.iid)).unsigned = true;
                    else if (typeof object.iid === "string")
                        message.iid = parseInt(object.iid, 10);
                    else if (typeof object.iid === "number")
                        message.iid = object.iid;
                    else if (typeof object.iid === "object")
                        message.iid = new $util.LongBits(object.iid.low >>> 0, object.iid.high >>> 0).toNumber(true);
                if (object.mappingId != null)
                    if ($util.Long)
                        (message.mappingId = $util.Long.fromValue(object.mappingId)).unsigned = true;
                    else if (typeof object.mappingId === "string")
                        message.mappingId = parseInt(object.mappingId, 10);
                    else if (typeof object.mappingId === "number")
                        message.mappingId = object.mappingId;
                    else if (typeof object.mappingId === "object")
                        message.mappingId = new $util.LongBits(object.mappingId.low >>> 0, object.mappingId.high >>> 0).toNumber(true);
                if (object.relPc != null)
                    if ($util.Long)
                        (message.relPc = $util.Long.fromValue(object.relPc)).unsigned = true;
                    else if (typeof object.relPc === "string")
                        message.relPc = parseInt(object.relPc, 10);
                    else if (typeof object.relPc === "number")
                        message.relPc = object.relPc;
                    else if (typeof object.relPc === "object")
                        message.relPc = new $util.LongBits(object.relPc.low >>> 0, object.relPc.high >>> 0).toNumber(true);
                return message;
            };

            /**
             * Creates a plain object from an UnsymbolizedSourceLocation message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {perfetto.protos.UnsymbolizedSourceLocation} message UnsymbolizedSourceLocation
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            UnsymbolizedSourceLocation.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.defaults) {
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.iid = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.iid = options.longs === String ? "0" : 0;
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.mappingId = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.mappingId = options.longs === String ? "0" : 0;
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.relPc = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.relPc = options.longs === String ? "0" : 0;
                }
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (typeof message.iid === "number")
                        object.iid = options.longs === String ? String(message.iid) : message.iid;
                    else
                        object.iid = options.longs === String ? $util.Long.prototype.toString.call(message.iid) : options.longs === Number ? new $util.LongBits(message.iid.low >>> 0, message.iid.high >>> 0).toNumber(true) : message.iid;
                if (message.mappingId != null && message.hasOwnProperty("mappingId"))
                    if (typeof message.mappingId === "number")
                        object.mappingId = options.longs === String ? String(message.mappingId) : message.mappingId;
                    else
                        object.mappingId = options.longs === String ? $util.Long.prototype.toString.call(message.mappingId) : options.longs === Number ? new $util.LongBits(message.mappingId.low >>> 0, message.mappingId.high >>> 0).toNumber(true) : message.mappingId;
                if (message.relPc != null && message.hasOwnProperty("relPc"))
                    if (typeof message.relPc === "number")
                        object.relPc = options.longs === String ? String(message.relPc) : message.relPc;
                    else
                        object.relPc = options.longs === String ? $util.Long.prototype.toString.call(message.relPc) : options.longs === Number ? new $util.LongBits(message.relPc.low >>> 0, message.relPc.high >>> 0).toNumber(true) : message.relPc;
                return object;
            };

            /**
             * Converts this UnsymbolizedSourceLocation to JSON.
             * @function toJSON
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            UnsymbolizedSourceLocation.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for UnsymbolizedSourceLocation
             * @function getTypeUrl
             * @memberof perfetto.protos.UnsymbolizedSourceLocation
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            UnsymbolizedSourceLocation.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.UnsymbolizedSourceLocation";
            };

            return UnsymbolizedSourceLocation;
        })();

        protos.SourceLocation = (function() {

            /**
             * Properties of a SourceLocation.
             * @memberof perfetto.protos
             * @interface ISourceLocation
             * @property {number|Long|null} [iid] SourceLocation iid
             * @property {string|null} [fileName] SourceLocation fileName
             * @property {string|null} [functionName] SourceLocation functionName
             * @property {number|null} [lineNumber] SourceLocation lineNumber
             */

            /**
             * Constructs a new SourceLocation.
             * @memberof perfetto.protos
             * @classdesc Represents a SourceLocation.
             * @implements ISourceLocation
             * @constructor
             * @param {perfetto.protos.ISourceLocation=} [properties] Properties to set
             */
            function SourceLocation(properties) {
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * SourceLocation iid.
             * @member {number|Long} iid
             * @memberof perfetto.protos.SourceLocation
             * @instance
             */
            SourceLocation.prototype.iid = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * SourceLocation fileName.
             * @member {string} fileName
             * @memberof perfetto.protos.SourceLocation
             * @instance
             */
            SourceLocation.prototype.fileName = "";

            /**
             * SourceLocation functionName.
             * @member {string} functionName
             * @memberof perfetto.protos.SourceLocation
             * @instance
             */
            SourceLocation.prototype.functionName = "";

            /**
             * SourceLocation lineNumber.
             * @member {number} lineNumber
             * @memberof perfetto.protos.SourceLocation
             * @instance
             */
            SourceLocation.prototype.lineNumber = 0;

            /**
             * Creates a new SourceLocation instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {perfetto.protos.ISourceLocation=} [properties] Properties to set
             * @returns {perfetto.protos.SourceLocation} SourceLocation instance
             */
            SourceLocation.create = function create(properties) {
                return new SourceLocation(properties);
            };

            /**
             * Encodes the specified SourceLocation message. Does not implicitly {@link perfetto.protos.SourceLocation.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {perfetto.protos.ISourceLocation} message SourceLocation message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            SourceLocation.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.iid != null && Object.hasOwnProperty.call(message, "iid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).uint64(message.iid);
                if (message.fileName != null && Object.hasOwnProperty.call(message, "fileName"))
                    writer.uint32(/* id 2, wireType 2 =*/18).string(message.fileName);
                if (message.functionName != null && Object.hasOwnProperty.call(message, "functionName"))
                    writer.uint32(/* id 3, wireType 2 =*/26).string(message.functionName);
                if (message.lineNumber != null && Object.hasOwnProperty.call(message, "lineNumber"))
                    writer.uint32(/* id 4, wireType 0 =*/32).uint32(message.lineNumber);
                return writer;
            };

            /**
             * Encodes the specified SourceLocation message, length delimited. Does not implicitly {@link perfetto.protos.SourceLocation.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {perfetto.protos.ISourceLocation} message SourceLocation message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            SourceLocation.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a SourceLocation message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.SourceLocation} SourceLocation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            SourceLocation.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.SourceLocation();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.iid = reader.uint64();
                            break;
                        }
                    case 2: {
                            message.fileName = reader.string();
                            break;
                        }
                    case 3: {
                            message.functionName = reader.string();
                            break;
                        }
                    case 4: {
                            message.lineNumber = reader.uint32();
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a SourceLocation message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.SourceLocation} SourceLocation
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            SourceLocation.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a SourceLocation message.
             * @function verify
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            SourceLocation.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (!$util.isInteger(message.iid) && !(message.iid && $util.isInteger(message.iid.low) && $util.isInteger(message.iid.high)))
                        return "iid: integer|Long expected";
                if (message.fileName != null && message.hasOwnProperty("fileName"))
                    if (!$util.isString(message.fileName))
                        return "fileName: string expected";
                if (message.functionName != null && message.hasOwnProperty("functionName"))
                    if (!$util.isString(message.functionName))
                        return "functionName: string expected";
                if (message.lineNumber != null && message.hasOwnProperty("lineNumber"))
                    if (!$util.isInteger(message.lineNumber))
                        return "lineNumber: integer expected";
                return null;
            };

            /**
             * Creates a SourceLocation message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.SourceLocation} SourceLocation
             */
            SourceLocation.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.SourceLocation)
                    return object;
                let message = new $root.perfetto.protos.SourceLocation();
                if (object.iid != null)
                    if ($util.Long)
                        (message.iid = $util.Long.fromValue(object.iid)).unsigned = true;
                    else if (typeof object.iid === "string")
                        message.iid = parseInt(object.iid, 10);
                    else if (typeof object.iid === "number")
                        message.iid = object.iid;
                    else if (typeof object.iid === "object")
                        message.iid = new $util.LongBits(object.iid.low >>> 0, object.iid.high >>> 0).toNumber(true);
                if (object.fileName != null)
                    message.fileName = String(object.fileName);
                if (object.functionName != null)
                    message.functionName = String(object.functionName);
                if (object.lineNumber != null)
                    message.lineNumber = object.lineNumber >>> 0;
                return message;
            };

            /**
             * Creates a plain object from a SourceLocation message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {perfetto.protos.SourceLocation} message SourceLocation
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            SourceLocation.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.defaults) {
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.iid = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.iid = options.longs === String ? "0" : 0;
                    object.fileName = "";
                    object.functionName = "";
                    object.lineNumber = 0;
                }
                if (message.iid != null && message.hasOwnProperty("iid"))
                    if (typeof message.iid === "number")
                        object.iid = options.longs === String ? String(message.iid) : message.iid;
                    else
                        object.iid = options.longs === String ? $util.Long.prototype.toString.call(message.iid) : options.longs === Number ? new $util.LongBits(message.iid.low >>> 0, message.iid.high >>> 0).toNumber(true) : message.iid;
                if (message.fileName != null && message.hasOwnProperty("fileName"))
                    object.fileName = message.fileName;
                if (message.functionName != null && message.hasOwnProperty("functionName"))
                    object.functionName = message.functionName;
                if (message.lineNumber != null && message.hasOwnProperty("lineNumber"))
                    object.lineNumber = message.lineNumber;
                return object;
            };

            /**
             * Converts this SourceLocation to JSON.
             * @function toJSON
             * @memberof perfetto.protos.SourceLocation
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            SourceLocation.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for SourceLocation
             * @function getTypeUrl
             * @memberof perfetto.protos.SourceLocation
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            SourceLocation.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.SourceLocation";
            };

            return SourceLocation;
        })();

        protos.ProcessDescriptor = (function() {

            /**
             * Properties of a ProcessDescriptor.
             * @memberof perfetto.protos
             * @interface IProcessDescriptor
             * @property {number|null} [pid] ProcessDescriptor pid
             * @property {Array.<string>|null} [cmdline] ProcessDescriptor cmdline
             * @property {string|null} [processName] ProcessDescriptor processName
             * @property {number|null} [processPriority] ProcessDescriptor processPriority
             * @property {number|Long|null} [startTimestampNs] ProcessDescriptor startTimestampNs
             * @property {perfetto.protos.ProcessDescriptor.ChromeProcessType|null} [chromeProcessType] ProcessDescriptor chromeProcessType
             * @property {number|null} [legacySortIndex] ProcessDescriptor legacySortIndex
             * @property {Array.<string>|null} [processLabels] ProcessDescriptor processLabels
             */

            /**
             * Constructs a new ProcessDescriptor.
             * @memberof perfetto.protos
             * @classdesc Represents a ProcessDescriptor.
             * @implements IProcessDescriptor
             * @constructor
             * @param {perfetto.protos.IProcessDescriptor=} [properties] Properties to set
             */
            function ProcessDescriptor(properties) {
                this.cmdline = [];
                this.processLabels = [];
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * ProcessDescriptor pid.
             * @member {number} pid
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             */
            ProcessDescriptor.prototype.pid = 0;

            /**
             * ProcessDescriptor cmdline.
             * @member {Array.<string>} cmdline
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             */
            ProcessDescriptor.prototype.cmdline = $util.emptyArray;

            /**
             * ProcessDescriptor processName.
             * @member {string} processName
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             */
            ProcessDescriptor.prototype.processName = "";

            /**
             * ProcessDescriptor processPriority.
             * @member {number} processPriority
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             */
            ProcessDescriptor.prototype.processPriority = 0;

            /**
             * ProcessDescriptor startTimestampNs.
             * @member {number|Long} startTimestampNs
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             */
            ProcessDescriptor.prototype.startTimestampNs = $util.Long ? $util.Long.fromBits(0,0,false) : 0;

            /**
             * ProcessDescriptor chromeProcessType.
             * @member {perfetto.protos.ProcessDescriptor.ChromeProcessType} chromeProcessType
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             */
            ProcessDescriptor.prototype.chromeProcessType = 0;

            /**
             * ProcessDescriptor legacySortIndex.
             * @member {number} legacySortIndex
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             */
            ProcessDescriptor.prototype.legacySortIndex = 0;

            /**
             * ProcessDescriptor processLabels.
             * @member {Array.<string>} processLabels
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             */
            ProcessDescriptor.prototype.processLabels = $util.emptyArray;

            /**
             * Creates a new ProcessDescriptor instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {perfetto.protos.IProcessDescriptor=} [properties] Properties to set
             * @returns {perfetto.protos.ProcessDescriptor} ProcessDescriptor instance
             */
            ProcessDescriptor.create = function create(properties) {
                return new ProcessDescriptor(properties);
            };

            /**
             * Encodes the specified ProcessDescriptor message. Does not implicitly {@link perfetto.protos.ProcessDescriptor.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {perfetto.protos.IProcessDescriptor} message ProcessDescriptor message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            ProcessDescriptor.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.pid != null && Object.hasOwnProperty.call(message, "pid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).int32(message.pid);
                if (message.cmdline != null && message.cmdline.length)
                    for (let i = 0; i < message.cmdline.length; ++i)
                        writer.uint32(/* id 2, wireType 2 =*/18).string(message.cmdline[i]);
                if (message.legacySortIndex != null && Object.hasOwnProperty.call(message, "legacySortIndex"))
                    writer.uint32(/* id 3, wireType 0 =*/24).int32(message.legacySortIndex);
                if (message.chromeProcessType != null && Object.hasOwnProperty.call(message, "chromeProcessType"))
                    writer.uint32(/* id 4, wireType 0 =*/32).int32(message.chromeProcessType);
                if (message.processPriority != null && Object.hasOwnProperty.call(message, "processPriority"))
                    writer.uint32(/* id 5, wireType 0 =*/40).int32(message.processPriority);
                if (message.processName != null && Object.hasOwnProperty.call(message, "processName"))
                    writer.uint32(/* id 6, wireType 2 =*/50).string(message.processName);
                if (message.startTimestampNs != null && Object.hasOwnProperty.call(message, "startTimestampNs"))
                    writer.uint32(/* id 7, wireType 0 =*/56).int64(message.startTimestampNs);
                if (message.processLabels != null && message.processLabels.length)
                    for (let i = 0; i < message.processLabels.length; ++i)
                        writer.uint32(/* id 8, wireType 2 =*/66).string(message.processLabels[i]);
                return writer;
            };

            /**
             * Encodes the specified ProcessDescriptor message, length delimited. Does not implicitly {@link perfetto.protos.ProcessDescriptor.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {perfetto.protos.IProcessDescriptor} message ProcessDescriptor message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            ProcessDescriptor.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a ProcessDescriptor message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.ProcessDescriptor} ProcessDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            ProcessDescriptor.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.ProcessDescriptor();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.pid = reader.int32();
                            break;
                        }
                    case 2: {
                            if (!(message.cmdline && message.cmdline.length))
                                message.cmdline = [];
                            message.cmdline.push(reader.string());
                            break;
                        }
                    case 6: {
                            message.processName = reader.string();
                            break;
                        }
                    case 5: {
                            message.processPriority = reader.int32();
                            break;
                        }
                    case 7: {
                            message.startTimestampNs = reader.int64();
                            break;
                        }
                    case 4: {
                            message.chromeProcessType = reader.int32();
                            break;
                        }
                    case 3: {
                            message.legacySortIndex = reader.int32();
                            break;
                        }
                    case 8: {
                            if (!(message.processLabels && message.processLabels.length))
                                message.processLabels = [];
                            message.processLabels.push(reader.string());
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a ProcessDescriptor message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.ProcessDescriptor} ProcessDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            ProcessDescriptor.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a ProcessDescriptor message.
             * @function verify
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            ProcessDescriptor.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.pid != null && message.hasOwnProperty("pid"))
                    if (!$util.isInteger(message.pid))
                        return "pid: integer expected";
                if (message.cmdline != null && message.hasOwnProperty("cmdline")) {
                    if (!Array.isArray(message.cmdline))
                        return "cmdline: array expected";
                    for (let i = 0; i < message.cmdline.length; ++i)
                        if (!$util.isString(message.cmdline[i]))
                            return "cmdline: string[] expected";
                }
                if (message.processName != null && message.hasOwnProperty("processName"))
                    if (!$util.isString(message.processName))
                        return "processName: string expected";
                if (message.processPriority != null && message.hasOwnProperty("processPriority"))
                    if (!$util.isInteger(message.processPriority))
                        return "processPriority: integer expected";
                if (message.startTimestampNs != null && message.hasOwnProperty("startTimestampNs"))
                    if (!$util.isInteger(message.startTimestampNs) && !(message.startTimestampNs && $util.isInteger(message.startTimestampNs.low) && $util.isInteger(message.startTimestampNs.high)))
                        return "startTimestampNs: integer|Long expected";
                if (message.chromeProcessType != null && message.hasOwnProperty("chromeProcessType"))
                    switch (message.chromeProcessType) {
                    default:
                        return "chromeProcessType: enum value expected";
                    case 0:
                    case 1:
                    case 2:
                    case 3:
                    case 4:
                    case 5:
                    case 6:
                    case 7:
                    case 8:
                        break;
                    }
                if (message.legacySortIndex != null && message.hasOwnProperty("legacySortIndex"))
                    if (!$util.isInteger(message.legacySortIndex))
                        return "legacySortIndex: integer expected";
                if (message.processLabels != null && message.hasOwnProperty("processLabels")) {
                    if (!Array.isArray(message.processLabels))
                        return "processLabels: array expected";
                    for (let i = 0; i < message.processLabels.length; ++i)
                        if (!$util.isString(message.processLabels[i]))
                            return "processLabels: string[] expected";
                }
                return null;
            };

            /**
             * Creates a ProcessDescriptor message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.ProcessDescriptor} ProcessDescriptor
             */
            ProcessDescriptor.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.ProcessDescriptor)
                    return object;
                let message = new $root.perfetto.protos.ProcessDescriptor();
                if (object.pid != null)
                    message.pid = object.pid | 0;
                if (object.cmdline) {
                    if (!Array.isArray(object.cmdline))
                        throw TypeError(".perfetto.protos.ProcessDescriptor.cmdline: array expected");
                    message.cmdline = [];
                    for (let i = 0; i < object.cmdline.length; ++i)
                        message.cmdline[i] = String(object.cmdline[i]);
                }
                if (object.processName != null)
                    message.processName = String(object.processName);
                if (object.processPriority != null)
                    message.processPriority = object.processPriority | 0;
                if (object.startTimestampNs != null)
                    if ($util.Long)
                        (message.startTimestampNs = $util.Long.fromValue(object.startTimestampNs)).unsigned = false;
                    else if (typeof object.startTimestampNs === "string")
                        message.startTimestampNs = parseInt(object.startTimestampNs, 10);
                    else if (typeof object.startTimestampNs === "number")
                        message.startTimestampNs = object.startTimestampNs;
                    else if (typeof object.startTimestampNs === "object")
                        message.startTimestampNs = new $util.LongBits(object.startTimestampNs.low >>> 0, object.startTimestampNs.high >>> 0).toNumber();
                switch (object.chromeProcessType) {
                default:
                    if (typeof object.chromeProcessType === "number") {
                        message.chromeProcessType = object.chromeProcessType;
                        break;
                    }
                    break;
                case "PROCESS_UNSPECIFIED":
                case 0:
                    message.chromeProcessType = 0;
                    break;
                case "PROCESS_BROWSER":
                case 1:
                    message.chromeProcessType = 1;
                    break;
                case "PROCESS_RENDERER":
                case 2:
                    message.chromeProcessType = 2;
                    break;
                case "PROCESS_UTILITY":
                case 3:
                    message.chromeProcessType = 3;
                    break;
                case "PROCESS_ZYGOTE":
                case 4:
                    message.chromeProcessType = 4;
                    break;
                case "PROCESS_SANDBOX_HELPER":
                case 5:
                    message.chromeProcessType = 5;
                    break;
                case "PROCESS_GPU":
                case 6:
                    message.chromeProcessType = 6;
                    break;
                case "PROCESS_PPAPI_PLUGIN":
                case 7:
                    message.chromeProcessType = 7;
                    break;
                case "PROCESS_PPAPI_BROKER":
                case 8:
                    message.chromeProcessType = 8;
                    break;
                }
                if (object.legacySortIndex != null)
                    message.legacySortIndex = object.legacySortIndex | 0;
                if (object.processLabels) {
                    if (!Array.isArray(object.processLabels))
                        throw TypeError(".perfetto.protos.ProcessDescriptor.processLabels: array expected");
                    message.processLabels = [];
                    for (let i = 0; i < object.processLabels.length; ++i)
                        message.processLabels[i] = String(object.processLabels[i]);
                }
                return message;
            };

            /**
             * Creates a plain object from a ProcessDescriptor message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {perfetto.protos.ProcessDescriptor} message ProcessDescriptor
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            ProcessDescriptor.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.arrays || options.defaults) {
                    object.cmdline = [];
                    object.processLabels = [];
                }
                if (options.defaults) {
                    object.pid = 0;
                    object.legacySortIndex = 0;
                    object.chromeProcessType = options.enums === String ? "PROCESS_UNSPECIFIED" : 0;
                    object.processPriority = 0;
                    object.processName = "";
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, false);
                        object.startTimestampNs = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.startTimestampNs = options.longs === String ? "0" : 0;
                }
                if (message.pid != null && message.hasOwnProperty("pid"))
                    object.pid = message.pid;
                if (message.cmdline && message.cmdline.length) {
                    object.cmdline = [];
                    for (let j = 0; j < message.cmdline.length; ++j)
                        object.cmdline[j] = message.cmdline[j];
                }
                if (message.legacySortIndex != null && message.hasOwnProperty("legacySortIndex"))
                    object.legacySortIndex = message.legacySortIndex;
                if (message.chromeProcessType != null && message.hasOwnProperty("chromeProcessType"))
                    object.chromeProcessType = options.enums === String ? $root.perfetto.protos.ProcessDescriptor.ChromeProcessType[message.chromeProcessType] === undefined ? message.chromeProcessType : $root.perfetto.protos.ProcessDescriptor.ChromeProcessType[message.chromeProcessType] : message.chromeProcessType;
                if (message.processPriority != null && message.hasOwnProperty("processPriority"))
                    object.processPriority = message.processPriority;
                if (message.processName != null && message.hasOwnProperty("processName"))
                    object.processName = message.processName;
                if (message.startTimestampNs != null && message.hasOwnProperty("startTimestampNs"))
                    if (typeof message.startTimestampNs === "number")
                        object.startTimestampNs = options.longs === String ? String(message.startTimestampNs) : message.startTimestampNs;
                    else
                        object.startTimestampNs = options.longs === String ? $util.Long.prototype.toString.call(message.startTimestampNs) : options.longs === Number ? new $util.LongBits(message.startTimestampNs.low >>> 0, message.startTimestampNs.high >>> 0).toNumber() : message.startTimestampNs;
                if (message.processLabels && message.processLabels.length) {
                    object.processLabels = [];
                    for (let j = 0; j < message.processLabels.length; ++j)
                        object.processLabels[j] = message.processLabels[j];
                }
                return object;
            };

            /**
             * Converts this ProcessDescriptor to JSON.
             * @function toJSON
             * @memberof perfetto.protos.ProcessDescriptor
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            ProcessDescriptor.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for ProcessDescriptor
             * @function getTypeUrl
             * @memberof perfetto.protos.ProcessDescriptor
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            ProcessDescriptor.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.ProcessDescriptor";
            };

            /**
             * ChromeProcessType enum.
             * @name perfetto.protos.ProcessDescriptor.ChromeProcessType
             * @enum {number}
             * @property {number} PROCESS_UNSPECIFIED=0 PROCESS_UNSPECIFIED value
             * @property {number} PROCESS_BROWSER=1 PROCESS_BROWSER value
             * @property {number} PROCESS_RENDERER=2 PROCESS_RENDERER value
             * @property {number} PROCESS_UTILITY=3 PROCESS_UTILITY value
             * @property {number} PROCESS_ZYGOTE=4 PROCESS_ZYGOTE value
             * @property {number} PROCESS_SANDBOX_HELPER=5 PROCESS_SANDBOX_HELPER value
             * @property {number} PROCESS_GPU=6 PROCESS_GPU value
             * @property {number} PROCESS_PPAPI_PLUGIN=7 PROCESS_PPAPI_PLUGIN value
             * @property {number} PROCESS_PPAPI_BROKER=8 PROCESS_PPAPI_BROKER value
             */
            ProcessDescriptor.ChromeProcessType = (function() {
                const valuesById = {}, values = Object.create(valuesById);
                values[valuesById[0] = "PROCESS_UNSPECIFIED"] = 0;
                values[valuesById[1] = "PROCESS_BROWSER"] = 1;
                values[valuesById[2] = "PROCESS_RENDERER"] = 2;
                values[valuesById[3] = "PROCESS_UTILITY"] = 3;
                values[valuesById[4] = "PROCESS_ZYGOTE"] = 4;
                values[valuesById[5] = "PROCESS_SANDBOX_HELPER"] = 5;
                values[valuesById[6] = "PROCESS_GPU"] = 6;
                values[valuesById[7] = "PROCESS_PPAPI_PLUGIN"] = 7;
                values[valuesById[8] = "PROCESS_PPAPI_BROKER"] = 8;
                return values;
            })();

            return ProcessDescriptor;
        })();

        protos.ThreadDescriptor = (function() {

            /**
             * Properties of a ThreadDescriptor.
             * @memberof perfetto.protos
             * @interface IThreadDescriptor
             * @property {number|null} [pid] ThreadDescriptor pid
             * @property {number|null} [tid] ThreadDescriptor tid
             * @property {string|null} [threadName] ThreadDescriptor threadName
             * @property {perfetto.protos.ThreadDescriptor.ChromeThreadType|null} [chromeThreadType] ThreadDescriptor chromeThreadType
             * @property {number|Long|null} [referenceTimestampUs] ThreadDescriptor referenceTimestampUs
             * @property {number|Long|null} [referenceThreadTimeUs] ThreadDescriptor referenceThreadTimeUs
             * @property {number|Long|null} [referenceThreadInstructionCount] ThreadDescriptor referenceThreadInstructionCount
             * @property {number|null} [legacySortIndex] ThreadDescriptor legacySortIndex
             */

            /**
             * Constructs a new ThreadDescriptor.
             * @memberof perfetto.protos
             * @classdesc Represents a ThreadDescriptor.
             * @implements IThreadDescriptor
             * @constructor
             * @param {perfetto.protos.IThreadDescriptor=} [properties] Properties to set
             */
            function ThreadDescriptor(properties) {
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * ThreadDescriptor pid.
             * @member {number} pid
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             */
            ThreadDescriptor.prototype.pid = 0;

            /**
             * ThreadDescriptor tid.
             * @member {number} tid
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             */
            ThreadDescriptor.prototype.tid = 0;

            /**
             * ThreadDescriptor threadName.
             * @member {string} threadName
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             */
            ThreadDescriptor.prototype.threadName = "";

            /**
             * ThreadDescriptor chromeThreadType.
             * @member {perfetto.protos.ThreadDescriptor.ChromeThreadType} chromeThreadType
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             */
            ThreadDescriptor.prototype.chromeThreadType = 0;

            /**
             * ThreadDescriptor referenceTimestampUs.
             * @member {number|Long} referenceTimestampUs
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             */
            ThreadDescriptor.prototype.referenceTimestampUs = $util.Long ? $util.Long.fromBits(0,0,false) : 0;

            /**
             * ThreadDescriptor referenceThreadTimeUs.
             * @member {number|Long} referenceThreadTimeUs
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             */
            ThreadDescriptor.prototype.referenceThreadTimeUs = $util.Long ? $util.Long.fromBits(0,0,false) : 0;

            /**
             * ThreadDescriptor referenceThreadInstructionCount.
             * @member {number|Long} referenceThreadInstructionCount
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             */
            ThreadDescriptor.prototype.referenceThreadInstructionCount = $util.Long ? $util.Long.fromBits(0,0,false) : 0;

            /**
             * ThreadDescriptor legacySortIndex.
             * @member {number} legacySortIndex
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             */
            ThreadDescriptor.prototype.legacySortIndex = 0;

            /**
             * Creates a new ThreadDescriptor instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {perfetto.protos.IThreadDescriptor=} [properties] Properties to set
             * @returns {perfetto.protos.ThreadDescriptor} ThreadDescriptor instance
             */
            ThreadDescriptor.create = function create(properties) {
                return new ThreadDescriptor(properties);
            };

            /**
             * Encodes the specified ThreadDescriptor message. Does not implicitly {@link perfetto.protos.ThreadDescriptor.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {perfetto.protos.IThreadDescriptor} message ThreadDescriptor message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            ThreadDescriptor.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.pid != null && Object.hasOwnProperty.call(message, "pid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).int32(message.pid);
                if (message.tid != null && Object.hasOwnProperty.call(message, "tid"))
                    writer.uint32(/* id 2, wireType 0 =*/16).int32(message.tid);
                if (message.legacySortIndex != null && Object.hasOwnProperty.call(message, "legacySortIndex"))
                    writer.uint32(/* id 3, wireType 0 =*/24).int32(message.legacySortIndex);
                if (message.chromeThreadType != null && Object.hasOwnProperty.call(message, "chromeThreadType"))
                    writer.uint32(/* id 4, wireType 0 =*/32).int32(message.chromeThreadType);
                if (message.threadName != null && Object.hasOwnProperty.call(message, "threadName"))
                    writer.uint32(/* id 5, wireType 2 =*/42).string(message.threadName);
                if (message.referenceTimestampUs != null && Object.hasOwnProperty.call(message, "referenceTimestampUs"))
                    writer.uint32(/* id 6, wireType 0 =*/48).int64(message.referenceTimestampUs);
                if (message.referenceThreadTimeUs != null && Object.hasOwnProperty.call(message, "referenceThreadTimeUs"))
                    writer.uint32(/* id 7, wireType 0 =*/56).int64(message.referenceThreadTimeUs);
                if (message.referenceThreadInstructionCount != null && Object.hasOwnProperty.call(message, "referenceThreadInstructionCount"))
                    writer.uint32(/* id 8, wireType 0 =*/64).int64(message.referenceThreadInstructionCount);
                return writer;
            };

            /**
             * Encodes the specified ThreadDescriptor message, length delimited. Does not implicitly {@link perfetto.protos.ThreadDescriptor.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {perfetto.protos.IThreadDescriptor} message ThreadDescriptor message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            ThreadDescriptor.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a ThreadDescriptor message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.ThreadDescriptor} ThreadDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            ThreadDescriptor.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.ThreadDescriptor();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.pid = reader.int32();
                            break;
                        }
                    case 2: {
                            message.tid = reader.int32();
                            break;
                        }
                    case 5: {
                            message.threadName = reader.string();
                            break;
                        }
                    case 4: {
                            message.chromeThreadType = reader.int32();
                            break;
                        }
                    case 6: {
                            message.referenceTimestampUs = reader.int64();
                            break;
                        }
                    case 7: {
                            message.referenceThreadTimeUs = reader.int64();
                            break;
                        }
                    case 8: {
                            message.referenceThreadInstructionCount = reader.int64();
                            break;
                        }
                    case 3: {
                            message.legacySortIndex = reader.int32();
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a ThreadDescriptor message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.ThreadDescriptor} ThreadDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            ThreadDescriptor.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a ThreadDescriptor message.
             * @function verify
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            ThreadDescriptor.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.pid != null && message.hasOwnProperty("pid"))
                    if (!$util.isInteger(message.pid))
                        return "pid: integer expected";
                if (message.tid != null && message.hasOwnProperty("tid"))
                    if (!$util.isInteger(message.tid))
                        return "tid: integer expected";
                if (message.threadName != null && message.hasOwnProperty("threadName"))
                    if (!$util.isString(message.threadName))
                        return "threadName: string expected";
                if (message.chromeThreadType != null && message.hasOwnProperty("chromeThreadType"))
                    switch (message.chromeThreadType) {
                    default:
                        return "chromeThreadType: enum value expected";
                    case 0:
                    case 1:
                    case 2:
                    case 3:
                    case 4:
                    case 5:
                    case 6:
                    case 7:
                    case 8:
                    case 9:
                    case 10:
                    case 11:
                    case 50:
                    case 51:
                        break;
                    }
                if (message.referenceTimestampUs != null && message.hasOwnProperty("referenceTimestampUs"))
                    if (!$util.isInteger(message.referenceTimestampUs) && !(message.referenceTimestampUs && $util.isInteger(message.referenceTimestampUs.low) && $util.isInteger(message.referenceTimestampUs.high)))
                        return "referenceTimestampUs: integer|Long expected";
                if (message.referenceThreadTimeUs != null && message.hasOwnProperty("referenceThreadTimeUs"))
                    if (!$util.isInteger(message.referenceThreadTimeUs) && !(message.referenceThreadTimeUs && $util.isInteger(message.referenceThreadTimeUs.low) && $util.isInteger(message.referenceThreadTimeUs.high)))
                        return "referenceThreadTimeUs: integer|Long expected";
                if (message.referenceThreadInstructionCount != null && message.hasOwnProperty("referenceThreadInstructionCount"))
                    if (!$util.isInteger(message.referenceThreadInstructionCount) && !(message.referenceThreadInstructionCount && $util.isInteger(message.referenceThreadInstructionCount.low) && $util.isInteger(message.referenceThreadInstructionCount.high)))
                        return "referenceThreadInstructionCount: integer|Long expected";
                if (message.legacySortIndex != null && message.hasOwnProperty("legacySortIndex"))
                    if (!$util.isInteger(message.legacySortIndex))
                        return "legacySortIndex: integer expected";
                return null;
            };

            /**
             * Creates a ThreadDescriptor message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.ThreadDescriptor} ThreadDescriptor
             */
            ThreadDescriptor.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.ThreadDescriptor)
                    return object;
                let message = new $root.perfetto.protos.ThreadDescriptor();
                if (object.pid != null)
                    message.pid = object.pid | 0;
                if (object.tid != null)
                    message.tid = object.tid | 0;
                if (object.threadName != null)
                    message.threadName = String(object.threadName);
                switch (object.chromeThreadType) {
                default:
                    if (typeof object.chromeThreadType === "number") {
                        message.chromeThreadType = object.chromeThreadType;
                        break;
                    }
                    break;
                case "CHROME_THREAD_UNSPECIFIED":
                case 0:
                    message.chromeThreadType = 0;
                    break;
                case "CHROME_THREAD_MAIN":
                case 1:
                    message.chromeThreadType = 1;
                    break;
                case "CHROME_THREAD_IO":
                case 2:
                    message.chromeThreadType = 2;
                    break;
                case "CHROME_THREAD_POOL_BG_WORKER":
                case 3:
                    message.chromeThreadType = 3;
                    break;
                case "CHROME_THREAD_POOL_FG_WORKER":
                case 4:
                    message.chromeThreadType = 4;
                    break;
                case "CHROME_THREAD_POOL_FB_BLOCKING":
                case 5:
                    message.chromeThreadType = 5;
                    break;
                case "CHROME_THREAD_POOL_BG_BLOCKING":
                case 6:
                    message.chromeThreadType = 6;
                    break;
                case "CHROME_THREAD_POOL_SERVICE":
                case 7:
                    message.chromeThreadType = 7;
                    break;
                case "CHROME_THREAD_COMPOSITOR":
                case 8:
                    message.chromeThreadType = 8;
                    break;
                case "CHROME_THREAD_VIZ_COMPOSITOR":
                case 9:
                    message.chromeThreadType = 9;
                    break;
                case "CHROME_THREAD_COMPOSITOR_WORKER":
                case 10:
                    message.chromeThreadType = 10;
                    break;
                case "CHROME_THREAD_SERVICE_WORKER":
                case 11:
                    message.chromeThreadType = 11;
                    break;
                case "CHROME_THREAD_MEMORY_INFRA":
                case 50:
                    message.chromeThreadType = 50;
                    break;
                case "CHROME_THREAD_SAMPLING_PROFILER":
                case 51:
                    message.chromeThreadType = 51;
                    break;
                }
                if (object.referenceTimestampUs != null)
                    if ($util.Long)
                        (message.referenceTimestampUs = $util.Long.fromValue(object.referenceTimestampUs)).unsigned = false;
                    else if (typeof object.referenceTimestampUs === "string")
                        message.referenceTimestampUs = parseInt(object.referenceTimestampUs, 10);
                    else if (typeof object.referenceTimestampUs === "number")
                        message.referenceTimestampUs = object.referenceTimestampUs;
                    else if (typeof object.referenceTimestampUs === "object")
                        message.referenceTimestampUs = new $util.LongBits(object.referenceTimestampUs.low >>> 0, object.referenceTimestampUs.high >>> 0).toNumber();
                if (object.referenceThreadTimeUs != null)
                    if ($util.Long)
                        (message.referenceThreadTimeUs = $util.Long.fromValue(object.referenceThreadTimeUs)).unsigned = false;
                    else if (typeof object.referenceThreadTimeUs === "string")
                        message.referenceThreadTimeUs = parseInt(object.referenceThreadTimeUs, 10);
                    else if (typeof object.referenceThreadTimeUs === "number")
                        message.referenceThreadTimeUs = object.referenceThreadTimeUs;
                    else if (typeof object.referenceThreadTimeUs === "object")
                        message.referenceThreadTimeUs = new $util.LongBits(object.referenceThreadTimeUs.low >>> 0, object.referenceThreadTimeUs.high >>> 0).toNumber();
                if (object.referenceThreadInstructionCount != null)
                    if ($util.Long)
                        (message.referenceThreadInstructionCount = $util.Long.fromValue(object.referenceThreadInstructionCount)).unsigned = false;
                    else if (typeof object.referenceThreadInstructionCount === "string")
                        message.referenceThreadInstructionCount = parseInt(object.referenceThreadInstructionCount, 10);
                    else if (typeof object.referenceThreadInstructionCount === "number")
                        message.referenceThreadInstructionCount = object.referenceThreadInstructionCount;
                    else if (typeof object.referenceThreadInstructionCount === "object")
                        message.referenceThreadInstructionCount = new $util.LongBits(object.referenceThreadInstructionCount.low >>> 0, object.referenceThreadInstructionCount.high >>> 0).toNumber();
                if (object.legacySortIndex != null)
                    message.legacySortIndex = object.legacySortIndex | 0;
                return message;
            };

            /**
             * Creates a plain object from a ThreadDescriptor message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {perfetto.protos.ThreadDescriptor} message ThreadDescriptor
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            ThreadDescriptor.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.defaults) {
                    object.pid = 0;
                    object.tid = 0;
                    object.legacySortIndex = 0;
                    object.chromeThreadType = options.enums === String ? "CHROME_THREAD_UNSPECIFIED" : 0;
                    object.threadName = "";
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, false);
                        object.referenceTimestampUs = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.referenceTimestampUs = options.longs === String ? "0" : 0;
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, false);
                        object.referenceThreadTimeUs = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.referenceThreadTimeUs = options.longs === String ? "0" : 0;
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, false);
                        object.referenceThreadInstructionCount = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.referenceThreadInstructionCount = options.longs === String ? "0" : 0;
                }
                if (message.pid != null && message.hasOwnProperty("pid"))
                    object.pid = message.pid;
                if (message.tid != null && message.hasOwnProperty("tid"))
                    object.tid = message.tid;
                if (message.legacySortIndex != null && message.hasOwnProperty("legacySortIndex"))
                    object.legacySortIndex = message.legacySortIndex;
                if (message.chromeThreadType != null && message.hasOwnProperty("chromeThreadType"))
                    object.chromeThreadType = options.enums === String ? $root.perfetto.protos.ThreadDescriptor.ChromeThreadType[message.chromeThreadType] === undefined ? message.chromeThreadType : $root.perfetto.protos.ThreadDescriptor.ChromeThreadType[message.chromeThreadType] : message.chromeThreadType;
                if (message.threadName != null && message.hasOwnProperty("threadName"))
                    object.threadName = message.threadName;
                if (message.referenceTimestampUs != null && message.hasOwnProperty("referenceTimestampUs"))
                    if (typeof message.referenceTimestampUs === "number")
                        object.referenceTimestampUs = options.longs === String ? String(message.referenceTimestampUs) : message.referenceTimestampUs;
                    else
                        object.referenceTimestampUs = options.longs === String ? $util.Long.prototype.toString.call(message.referenceTimestampUs) : options.longs === Number ? new $util.LongBits(message.referenceTimestampUs.low >>> 0, message.referenceTimestampUs.high >>> 0).toNumber() : message.referenceTimestampUs;
                if (message.referenceThreadTimeUs != null && message.hasOwnProperty("referenceThreadTimeUs"))
                    if (typeof message.referenceThreadTimeUs === "number")
                        object.referenceThreadTimeUs = options.longs === String ? String(message.referenceThreadTimeUs) : message.referenceThreadTimeUs;
                    else
                        object.referenceThreadTimeUs = options.longs === String ? $util.Long.prototype.toString.call(message.referenceThreadTimeUs) : options.longs === Number ? new $util.LongBits(message.referenceThreadTimeUs.low >>> 0, message.referenceThreadTimeUs.high >>> 0).toNumber() : message.referenceThreadTimeUs;
                if (message.referenceThreadInstructionCount != null && message.hasOwnProperty("referenceThreadInstructionCount"))
                    if (typeof message.referenceThreadInstructionCount === "number")
                        object.referenceThreadInstructionCount = options.longs === String ? String(message.referenceThreadInstructionCount) : message.referenceThreadInstructionCount;
                    else
                        object.referenceThreadInstructionCount = options.longs === String ? $util.Long.prototype.toString.call(message.referenceThreadInstructionCount) : options.longs === Number ? new $util.LongBits(message.referenceThreadInstructionCount.low >>> 0, message.referenceThreadInstructionCount.high >>> 0).toNumber() : message.referenceThreadInstructionCount;
                return object;
            };

            /**
             * Converts this ThreadDescriptor to JSON.
             * @function toJSON
             * @memberof perfetto.protos.ThreadDescriptor
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            ThreadDescriptor.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for ThreadDescriptor
             * @function getTypeUrl
             * @memberof perfetto.protos.ThreadDescriptor
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            ThreadDescriptor.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.ThreadDescriptor";
            };

            /**
             * ChromeThreadType enum.
             * @name perfetto.protos.ThreadDescriptor.ChromeThreadType
             * @enum {number}
             * @property {number} CHROME_THREAD_UNSPECIFIED=0 CHROME_THREAD_UNSPECIFIED value
             * @property {number} CHROME_THREAD_MAIN=1 CHROME_THREAD_MAIN value
             * @property {number} CHROME_THREAD_IO=2 CHROME_THREAD_IO value
             * @property {number} CHROME_THREAD_POOL_BG_WORKER=3 CHROME_THREAD_POOL_BG_WORKER value
             * @property {number} CHROME_THREAD_POOL_FG_WORKER=4 CHROME_THREAD_POOL_FG_WORKER value
             * @property {number} CHROME_THREAD_POOL_FB_BLOCKING=5 CHROME_THREAD_POOL_FB_BLOCKING value
             * @property {number} CHROME_THREAD_POOL_BG_BLOCKING=6 CHROME_THREAD_POOL_BG_BLOCKING value
             * @property {number} CHROME_THREAD_POOL_SERVICE=7 CHROME_THREAD_POOL_SERVICE value
             * @property {number} CHROME_THREAD_COMPOSITOR=8 CHROME_THREAD_COMPOSITOR value
             * @property {number} CHROME_THREAD_VIZ_COMPOSITOR=9 CHROME_THREAD_VIZ_COMPOSITOR value
             * @property {number} CHROME_THREAD_COMPOSITOR_WORKER=10 CHROME_THREAD_COMPOSITOR_WORKER value
             * @property {number} CHROME_THREAD_SERVICE_WORKER=11 CHROME_THREAD_SERVICE_WORKER value
             * @property {number} CHROME_THREAD_MEMORY_INFRA=50 CHROME_THREAD_MEMORY_INFRA value
             * @property {number} CHROME_THREAD_SAMPLING_PROFILER=51 CHROME_THREAD_SAMPLING_PROFILER value
             */
            ThreadDescriptor.ChromeThreadType = (function() {
                const valuesById = {}, values = Object.create(valuesById);
                values[valuesById[0] = "CHROME_THREAD_UNSPECIFIED"] = 0;
                values[valuesById[1] = "CHROME_THREAD_MAIN"] = 1;
                values[valuesById[2] = "CHROME_THREAD_IO"] = 2;
                values[valuesById[3] = "CHROME_THREAD_POOL_BG_WORKER"] = 3;
                values[valuesById[4] = "CHROME_THREAD_POOL_FG_WORKER"] = 4;
                values[valuesById[5] = "CHROME_THREAD_POOL_FB_BLOCKING"] = 5;
                values[valuesById[6] = "CHROME_THREAD_POOL_BG_BLOCKING"] = 6;
                values[valuesById[7] = "CHROME_THREAD_POOL_SERVICE"] = 7;
                values[valuesById[8] = "CHROME_THREAD_COMPOSITOR"] = 8;
                values[valuesById[9] = "CHROME_THREAD_VIZ_COMPOSITOR"] = 9;
                values[valuesById[10] = "CHROME_THREAD_COMPOSITOR_WORKER"] = 10;
                values[valuesById[11] = "CHROME_THREAD_SERVICE_WORKER"] = 11;
                values[valuesById[50] = "CHROME_THREAD_MEMORY_INFRA"] = 50;
                values[valuesById[51] = "CHROME_THREAD_SAMPLING_PROFILER"] = 51;
                return values;
            })();

            return ThreadDescriptor;
        })();

        protos.TrackDescriptor = (function() {

            /**
             * Properties of a TrackDescriptor.
             * @memberof perfetto.protos
             * @interface ITrackDescriptor
             * @property {number|Long|null} [uuid] TrackDescriptor uuid
             * @property {number|Long|null} [parentUuid] TrackDescriptor parentUuid
             * @property {string|null} [name] TrackDescriptor name
             * @property {perfetto.protos.IProcessDescriptor|null} [process] TrackDescriptor process
             * @property {perfetto.protos.IThreadDescriptor|null} [thread] TrackDescriptor thread
             */

            /**
             * Constructs a new TrackDescriptor.
             * @memberof perfetto.protos
             * @classdesc Represents a TrackDescriptor.
             * @implements ITrackDescriptor
             * @constructor
             * @param {perfetto.protos.ITrackDescriptor=} [properties] Properties to set
             */
            function TrackDescriptor(properties) {
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * TrackDescriptor uuid.
             * @member {number|Long} uuid
             * @memberof perfetto.protos.TrackDescriptor
             * @instance
             */
            TrackDescriptor.prototype.uuid = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * TrackDescriptor parentUuid.
             * @member {number|Long} parentUuid
             * @memberof perfetto.protos.TrackDescriptor
             * @instance
             */
            TrackDescriptor.prototype.parentUuid = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * TrackDescriptor name.
             * @member {string} name
             * @memberof perfetto.protos.TrackDescriptor
             * @instance
             */
            TrackDescriptor.prototype.name = "";

            /**
             * TrackDescriptor process.
             * @member {perfetto.protos.IProcessDescriptor|null|undefined} process
             * @memberof perfetto.protos.TrackDescriptor
             * @instance
             */
            TrackDescriptor.prototype.process = null;

            /**
             * TrackDescriptor thread.
             * @member {perfetto.protos.IThreadDescriptor|null|undefined} thread
             * @memberof perfetto.protos.TrackDescriptor
             * @instance
             */
            TrackDescriptor.prototype.thread = null;

            /**
             * Creates a new TrackDescriptor instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {perfetto.protos.ITrackDescriptor=} [properties] Properties to set
             * @returns {perfetto.protos.TrackDescriptor} TrackDescriptor instance
             */
            TrackDescriptor.create = function create(properties) {
                return new TrackDescriptor(properties);
            };

            /**
             * Encodes the specified TrackDescriptor message. Does not implicitly {@link perfetto.protos.TrackDescriptor.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {perfetto.protos.ITrackDescriptor} message TrackDescriptor message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            TrackDescriptor.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.uuid != null && Object.hasOwnProperty.call(message, "uuid"))
                    writer.uint32(/* id 1, wireType 0 =*/8).uint64(message.uuid);
                if (message.name != null && Object.hasOwnProperty.call(message, "name"))
                    writer.uint32(/* id 2, wireType 2 =*/18).string(message.name);
                if (message.process != null && Object.hasOwnProperty.call(message, "process"))
                    $root.perfetto.protos.ProcessDescriptor.encode(message.process, writer.uint32(/* id 3, wireType 2 =*/26).fork()).ldelim();
                if (message.thread != null && Object.hasOwnProperty.call(message, "thread"))
                    $root.perfetto.protos.ThreadDescriptor.encode(message.thread, writer.uint32(/* id 4, wireType 2 =*/34).fork()).ldelim();
                if (message.parentUuid != null && Object.hasOwnProperty.call(message, "parentUuid"))
                    writer.uint32(/* id 5, wireType 0 =*/40).uint64(message.parentUuid);
                return writer;
            };

            /**
             * Encodes the specified TrackDescriptor message, length delimited. Does not implicitly {@link perfetto.protos.TrackDescriptor.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {perfetto.protos.ITrackDescriptor} message TrackDescriptor message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            TrackDescriptor.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a TrackDescriptor message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.TrackDescriptor} TrackDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            TrackDescriptor.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.TrackDescriptor();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            message.uuid = reader.uint64();
                            break;
                        }
                    case 5: {
                            message.parentUuid = reader.uint64();
                            break;
                        }
                    case 2: {
                            message.name = reader.string();
                            break;
                        }
                    case 3: {
                            message.process = $root.perfetto.protos.ProcessDescriptor.decode(reader, reader.uint32());
                            break;
                        }
                    case 4: {
                            message.thread = $root.perfetto.protos.ThreadDescriptor.decode(reader, reader.uint32());
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a TrackDescriptor message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.TrackDescriptor} TrackDescriptor
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            TrackDescriptor.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a TrackDescriptor message.
             * @function verify
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            TrackDescriptor.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.uuid != null && message.hasOwnProperty("uuid"))
                    if (!$util.isInteger(message.uuid) && !(message.uuid && $util.isInteger(message.uuid.low) && $util.isInteger(message.uuid.high)))
                        return "uuid: integer|Long expected";
                if (message.parentUuid != null && message.hasOwnProperty("parentUuid"))
                    if (!$util.isInteger(message.parentUuid) && !(message.parentUuid && $util.isInteger(message.parentUuid.low) && $util.isInteger(message.parentUuid.high)))
                        return "parentUuid: integer|Long expected";
                if (message.name != null && message.hasOwnProperty("name"))
                    if (!$util.isString(message.name))
                        return "name: string expected";
                if (message.process != null && message.hasOwnProperty("process")) {
                    let error = $root.perfetto.protos.ProcessDescriptor.verify(message.process);
                    if (error)
                        return "process." + error;
                }
                if (message.thread != null && message.hasOwnProperty("thread")) {
                    let error = $root.perfetto.protos.ThreadDescriptor.verify(message.thread);
                    if (error)
                        return "thread." + error;
                }
                return null;
            };

            /**
             * Creates a TrackDescriptor message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.TrackDescriptor} TrackDescriptor
             */
            TrackDescriptor.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.TrackDescriptor)
                    return object;
                let message = new $root.perfetto.protos.TrackDescriptor();
                if (object.uuid != null)
                    if ($util.Long)
                        (message.uuid = $util.Long.fromValue(object.uuid)).unsigned = true;
                    else if (typeof object.uuid === "string")
                        message.uuid = parseInt(object.uuid, 10);
                    else if (typeof object.uuid === "number")
                        message.uuid = object.uuid;
                    else if (typeof object.uuid === "object")
                        message.uuid = new $util.LongBits(object.uuid.low >>> 0, object.uuid.high >>> 0).toNumber(true);
                if (object.parentUuid != null)
                    if ($util.Long)
                        (message.parentUuid = $util.Long.fromValue(object.parentUuid)).unsigned = true;
                    else if (typeof object.parentUuid === "string")
                        message.parentUuid = parseInt(object.parentUuid, 10);
                    else if (typeof object.parentUuid === "number")
                        message.parentUuid = object.parentUuid;
                    else if (typeof object.parentUuid === "object")
                        message.parentUuid = new $util.LongBits(object.parentUuid.low >>> 0, object.parentUuid.high >>> 0).toNumber(true);
                if (object.name != null)
                    message.name = String(object.name);
                if (object.process != null) {
                    if (typeof object.process !== "object")
                        throw TypeError(".perfetto.protos.TrackDescriptor.process: object expected");
                    message.process = $root.perfetto.protos.ProcessDescriptor.fromObject(object.process);
                }
                if (object.thread != null) {
                    if (typeof object.thread !== "object")
                        throw TypeError(".perfetto.protos.TrackDescriptor.thread: object expected");
                    message.thread = $root.perfetto.protos.ThreadDescriptor.fromObject(object.thread);
                }
                return message;
            };

            /**
             * Creates a plain object from a TrackDescriptor message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {perfetto.protos.TrackDescriptor} message TrackDescriptor
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            TrackDescriptor.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.defaults) {
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.uuid = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.uuid = options.longs === String ? "0" : 0;
                    object.name = "";
                    object.process = null;
                    object.thread = null;
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.parentUuid = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.parentUuid = options.longs === String ? "0" : 0;
                }
                if (message.uuid != null && message.hasOwnProperty("uuid"))
                    if (typeof message.uuid === "number")
                        object.uuid = options.longs === String ? String(message.uuid) : message.uuid;
                    else
                        object.uuid = options.longs === String ? $util.Long.prototype.toString.call(message.uuid) : options.longs === Number ? new $util.LongBits(message.uuid.low >>> 0, message.uuid.high >>> 0).toNumber(true) : message.uuid;
                if (message.name != null && message.hasOwnProperty("name"))
                    object.name = message.name;
                if (message.process != null && message.hasOwnProperty("process"))
                    object.process = $root.perfetto.protos.ProcessDescriptor.toObject(message.process, options);
                if (message.thread != null && message.hasOwnProperty("thread"))
                    object.thread = $root.perfetto.protos.ThreadDescriptor.toObject(message.thread, options);
                if (message.parentUuid != null && message.hasOwnProperty("parentUuid"))
                    if (typeof message.parentUuid === "number")
                        object.parentUuid = options.longs === String ? String(message.parentUuid) : message.parentUuid;
                    else
                        object.parentUuid = options.longs === String ? $util.Long.prototype.toString.call(message.parentUuid) : options.longs === Number ? new $util.LongBits(message.parentUuid.low >>> 0, message.parentUuid.high >>> 0).toNumber(true) : message.parentUuid;
                return object;
            };

            /**
             * Converts this TrackDescriptor to JSON.
             * @function toJSON
             * @memberof perfetto.protos.TrackDescriptor
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            TrackDescriptor.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for TrackDescriptor
             * @function getTypeUrl
             * @memberof perfetto.protos.TrackDescriptor
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            TrackDescriptor.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.TrackDescriptor";
            };

            return TrackDescriptor;
        })();

        protos.TrackEvent = (function() {

            /**
             * Properties of a TrackEvent.
             * @memberof perfetto.protos
             * @interface ITrackEvent
             * @property {Array.<number|Long>|null} [categoryIids] TrackEvent categoryIids
             * @property {Array.<string>|null} [categories] TrackEvent categories
             * @property {number|Long|null} [nameIid] TrackEvent nameIid
             * @property {string|null} [name] TrackEvent name
             * @property {perfetto.protos.TrackEvent.Type|null} [type] TrackEvent type
             * @property {number|Long|null} [trackUuid] TrackEvent trackUuid
             * @property {number|Long|null} [counterValue] TrackEvent counterValue
             * @property {number|null} [doubleCounterValue] TrackEvent doubleCounterValue
             * @property {Array.<number|Long>|null} [extraCounterTrackUuids] TrackEvent extraCounterTrackUuids
             * @property {Array.<number|Long>|null} [extraCounterValues] TrackEvent extraCounterValues
             * @property {Array.<number|Long>|null} [extraDoubleCounterTrackUuids] TrackEvent extraDoubleCounterTrackUuids
             * @property {Array.<number>|null} [extraDoubleCounterValues] TrackEvent extraDoubleCounterValues
             * @property {Array.<number|Long>|null} [flowIdsOld] TrackEvent flowIdsOld
             * @property {Array.<number|Long>|null} [flowIds] TrackEvent flowIds
             * @property {Array.<number|Long>|null} [terminatingFlowIdsOld] TrackEvent terminatingFlowIdsOld
             * @property {Array.<number|Long>|null} [terminatingFlowIds] TrackEvent terminatingFlowIds
             * @property {Array.<perfetto.protos.IDebugAnnotation>|null} [debugAnnotations] TrackEvent debugAnnotations
             * @property {perfetto.protos.ISourceLocation|null} [sourceLocation] TrackEvent sourceLocation
             * @property {number|Long|null} [sourceLocationIid] TrackEvent sourceLocationIid
             */

            /**
             * Constructs a new TrackEvent.
             * @memberof perfetto.protos
             * @classdesc Represents a TrackEvent.
             * @implements ITrackEvent
             * @constructor
             * @param {perfetto.protos.ITrackEvent=} [properties] Properties to set
             */
            function TrackEvent(properties) {
                this.categoryIids = [];
                this.categories = [];
                this.extraCounterTrackUuids = [];
                this.extraCounterValues = [];
                this.extraDoubleCounterTrackUuids = [];
                this.extraDoubleCounterValues = [];
                this.flowIdsOld = [];
                this.flowIds = [];
                this.terminatingFlowIdsOld = [];
                this.terminatingFlowIds = [];
                this.debugAnnotations = [];
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * TrackEvent categoryIids.
             * @member {Array.<number|Long>} categoryIids
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.categoryIids = $util.emptyArray;

            /**
             * TrackEvent categories.
             * @member {Array.<string>} categories
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.categories = $util.emptyArray;

            /**
             * TrackEvent nameIid.
             * @member {number|Long|null|undefined} nameIid
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.nameIid = null;

            /**
             * TrackEvent name.
             * @member {string|null|undefined} name
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.name = null;

            /**
             * TrackEvent type.
             * @member {perfetto.protos.TrackEvent.Type} type
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.type = 0;

            /**
             * TrackEvent trackUuid.
             * @member {number|Long} trackUuid
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.trackUuid = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * TrackEvent counterValue.
             * @member {number|Long|null|undefined} counterValue
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.counterValue = null;

            /**
             * TrackEvent doubleCounterValue.
             * @member {number|null|undefined} doubleCounterValue
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.doubleCounterValue = null;

            /**
             * TrackEvent extraCounterTrackUuids.
             * @member {Array.<number|Long>} extraCounterTrackUuids
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.extraCounterTrackUuids = $util.emptyArray;

            /**
             * TrackEvent extraCounterValues.
             * @member {Array.<number|Long>} extraCounterValues
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.extraCounterValues = $util.emptyArray;

            /**
             * TrackEvent extraDoubleCounterTrackUuids.
             * @member {Array.<number|Long>} extraDoubleCounterTrackUuids
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.extraDoubleCounterTrackUuids = $util.emptyArray;

            /**
             * TrackEvent extraDoubleCounterValues.
             * @member {Array.<number>} extraDoubleCounterValues
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.extraDoubleCounterValues = $util.emptyArray;

            /**
             * TrackEvent flowIdsOld.
             * @member {Array.<number|Long>} flowIdsOld
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.flowIdsOld = $util.emptyArray;

            /**
             * TrackEvent flowIds.
             * @member {Array.<number|Long>} flowIds
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.flowIds = $util.emptyArray;

            /**
             * TrackEvent terminatingFlowIdsOld.
             * @member {Array.<number|Long>} terminatingFlowIdsOld
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.terminatingFlowIdsOld = $util.emptyArray;

            /**
             * TrackEvent terminatingFlowIds.
             * @member {Array.<number|Long>} terminatingFlowIds
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.terminatingFlowIds = $util.emptyArray;

            /**
             * TrackEvent debugAnnotations.
             * @member {Array.<perfetto.protos.IDebugAnnotation>} debugAnnotations
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.debugAnnotations = $util.emptyArray;

            /**
             * TrackEvent sourceLocation.
             * @member {perfetto.protos.ISourceLocation|null|undefined} sourceLocation
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.sourceLocation = null;

            /**
             * TrackEvent sourceLocationIid.
             * @member {number|Long|null|undefined} sourceLocationIid
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            TrackEvent.prototype.sourceLocationIid = null;

            // OneOf field names bound to virtual getters and setters
            let $oneOfFields;

            /**
             * TrackEvent nameField.
             * @member {"nameIid"|"name"|undefined} nameField
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            Object.defineProperty(TrackEvent.prototype, "nameField", {
                get: $util.oneOfGetter($oneOfFields = ["nameIid", "name"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * TrackEvent counterValueField.
             * @member {"counterValue"|"doubleCounterValue"|undefined} counterValueField
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            Object.defineProperty(TrackEvent.prototype, "counterValueField", {
                get: $util.oneOfGetter($oneOfFields = ["counterValue", "doubleCounterValue"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * TrackEvent sourceLocationField.
             * @member {"sourceLocation"|"sourceLocationIid"|undefined} sourceLocationField
             * @memberof perfetto.protos.TrackEvent
             * @instance
             */
            Object.defineProperty(TrackEvent.prototype, "sourceLocationField", {
                get: $util.oneOfGetter($oneOfFields = ["sourceLocation", "sourceLocationIid"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * Creates a new TrackEvent instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {perfetto.protos.ITrackEvent=} [properties] Properties to set
             * @returns {perfetto.protos.TrackEvent} TrackEvent instance
             */
            TrackEvent.create = function create(properties) {
                return new TrackEvent(properties);
            };

            /**
             * Encodes the specified TrackEvent message. Does not implicitly {@link perfetto.protos.TrackEvent.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {perfetto.protos.ITrackEvent} message TrackEvent message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            TrackEvent.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.categoryIids != null && message.categoryIids.length)
                    for (let i = 0; i < message.categoryIids.length; ++i)
                        writer.uint32(/* id 3, wireType 0 =*/24).uint64(message.categoryIids[i]);
                if (message.debugAnnotations != null && message.debugAnnotations.length)
                    for (let i = 0; i < message.debugAnnotations.length; ++i)
                        $root.perfetto.protos.DebugAnnotation.encode(message.debugAnnotations[i], writer.uint32(/* id 4, wireType 2 =*/34).fork()).ldelim();
                if (message.type != null && Object.hasOwnProperty.call(message, "type"))
                    writer.uint32(/* id 9, wireType 0 =*/72).int32(message.type);
                if (message.nameIid != null && Object.hasOwnProperty.call(message, "nameIid"))
                    writer.uint32(/* id 10, wireType 0 =*/80).uint64(message.nameIid);
                if (message.trackUuid != null && Object.hasOwnProperty.call(message, "trackUuid"))
                    writer.uint32(/* id 11, wireType 0 =*/88).uint64(message.trackUuid);
                if (message.extraCounterValues != null && message.extraCounterValues.length)
                    for (let i = 0; i < message.extraCounterValues.length; ++i)
                        writer.uint32(/* id 12, wireType 0 =*/96).int64(message.extraCounterValues[i]);
                if (message.categories != null && message.categories.length)
                    for (let i = 0; i < message.categories.length; ++i)
                        writer.uint32(/* id 22, wireType 2 =*/178).string(message.categories[i]);
                if (message.name != null && Object.hasOwnProperty.call(message, "name"))
                    writer.uint32(/* id 23, wireType 2 =*/186).string(message.name);
                if (message.counterValue != null && Object.hasOwnProperty.call(message, "counterValue"))
                    writer.uint32(/* id 30, wireType 0 =*/240).int64(message.counterValue);
                if (message.extraCounterTrackUuids != null && message.extraCounterTrackUuids.length)
                    for (let i = 0; i < message.extraCounterTrackUuids.length; ++i)
                        writer.uint32(/* id 31, wireType 0 =*/248).uint64(message.extraCounterTrackUuids[i]);
                if (message.sourceLocation != null && Object.hasOwnProperty.call(message, "sourceLocation"))
                    $root.perfetto.protos.SourceLocation.encode(message.sourceLocation, writer.uint32(/* id 33, wireType 2 =*/266).fork()).ldelim();
                if (message.sourceLocationIid != null && Object.hasOwnProperty.call(message, "sourceLocationIid"))
                    writer.uint32(/* id 34, wireType 0 =*/272).uint64(message.sourceLocationIid);
                if (message.flowIdsOld != null && message.flowIdsOld.length)
                    for (let i = 0; i < message.flowIdsOld.length; ++i)
                        writer.uint32(/* id 36, wireType 0 =*/288).uint64(message.flowIdsOld[i]);
                if (message.terminatingFlowIdsOld != null && message.terminatingFlowIdsOld.length)
                    for (let i = 0; i < message.terminatingFlowIdsOld.length; ++i)
                        writer.uint32(/* id 42, wireType 0 =*/336).uint64(message.terminatingFlowIdsOld[i]);
                if (message.doubleCounterValue != null && Object.hasOwnProperty.call(message, "doubleCounterValue"))
                    writer.uint32(/* id 44, wireType 1 =*/353).double(message.doubleCounterValue);
                if (message.extraDoubleCounterTrackUuids != null && message.extraDoubleCounterTrackUuids.length)
                    for (let i = 0; i < message.extraDoubleCounterTrackUuids.length; ++i)
                        writer.uint32(/* id 45, wireType 0 =*/360).uint64(message.extraDoubleCounterTrackUuids[i]);
                if (message.extraDoubleCounterValues != null && message.extraDoubleCounterValues.length)
                    for (let i = 0; i < message.extraDoubleCounterValues.length; ++i)
                        writer.uint32(/* id 46, wireType 1 =*/369).double(message.extraDoubleCounterValues[i]);
                if (message.flowIds != null && message.flowIds.length)
                    for (let i = 0; i < message.flowIds.length; ++i)
                        writer.uint32(/* id 47, wireType 1 =*/377).fixed64(message.flowIds[i]);
                if (message.terminatingFlowIds != null && message.terminatingFlowIds.length)
                    for (let i = 0; i < message.terminatingFlowIds.length; ++i)
                        writer.uint32(/* id 48, wireType 1 =*/385).fixed64(message.terminatingFlowIds[i]);
                return writer;
            };

            /**
             * Encodes the specified TrackEvent message, length delimited. Does not implicitly {@link perfetto.protos.TrackEvent.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {perfetto.protos.ITrackEvent} message TrackEvent message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            TrackEvent.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a TrackEvent message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.TrackEvent} TrackEvent
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            TrackEvent.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.TrackEvent();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 3: {
                            if (!(message.categoryIids && message.categoryIids.length))
                                message.categoryIids = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.categoryIids.push(reader.uint64());
                            } else
                                message.categoryIids.push(reader.uint64());
                            break;
                        }
                    case 22: {
                            if (!(message.categories && message.categories.length))
                                message.categories = [];
                            message.categories.push(reader.string());
                            break;
                        }
                    case 10: {
                            message.nameIid = reader.uint64();
                            break;
                        }
                    case 23: {
                            message.name = reader.string();
                            break;
                        }
                    case 9: {
                            message.type = reader.int32();
                            break;
                        }
                    case 11: {
                            message.trackUuid = reader.uint64();
                            break;
                        }
                    case 30: {
                            message.counterValue = reader.int64();
                            break;
                        }
                    case 44: {
                            message.doubleCounterValue = reader.double();
                            break;
                        }
                    case 31: {
                            if (!(message.extraCounterTrackUuids && message.extraCounterTrackUuids.length))
                                message.extraCounterTrackUuids = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.extraCounterTrackUuids.push(reader.uint64());
                            } else
                                message.extraCounterTrackUuids.push(reader.uint64());
                            break;
                        }
                    case 12: {
                            if (!(message.extraCounterValues && message.extraCounterValues.length))
                                message.extraCounterValues = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.extraCounterValues.push(reader.int64());
                            } else
                                message.extraCounterValues.push(reader.int64());
                            break;
                        }
                    case 45: {
                            if (!(message.extraDoubleCounterTrackUuids && message.extraDoubleCounterTrackUuids.length))
                                message.extraDoubleCounterTrackUuids = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.extraDoubleCounterTrackUuids.push(reader.uint64());
                            } else
                                message.extraDoubleCounterTrackUuids.push(reader.uint64());
                            break;
                        }
                    case 46: {
                            if (!(message.extraDoubleCounterValues && message.extraDoubleCounterValues.length))
                                message.extraDoubleCounterValues = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.extraDoubleCounterValues.push(reader.double());
                            } else
                                message.extraDoubleCounterValues.push(reader.double());
                            break;
                        }
                    case 36: {
                            if (!(message.flowIdsOld && message.flowIdsOld.length))
                                message.flowIdsOld = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.flowIdsOld.push(reader.uint64());
                            } else
                                message.flowIdsOld.push(reader.uint64());
                            break;
                        }
                    case 47: {
                            if (!(message.flowIds && message.flowIds.length))
                                message.flowIds = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.flowIds.push(reader.fixed64());
                            } else
                                message.flowIds.push(reader.fixed64());
                            break;
                        }
                    case 42: {
                            if (!(message.terminatingFlowIdsOld && message.terminatingFlowIdsOld.length))
                                message.terminatingFlowIdsOld = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.terminatingFlowIdsOld.push(reader.uint64());
                            } else
                                message.terminatingFlowIdsOld.push(reader.uint64());
                            break;
                        }
                    case 48: {
                            if (!(message.terminatingFlowIds && message.terminatingFlowIds.length))
                                message.terminatingFlowIds = [];
                            if ((tag & 7) === 2) {
                                let end2 = reader.uint32() + reader.pos;
                                while (reader.pos < end2)
                                    message.terminatingFlowIds.push(reader.fixed64());
                            } else
                                message.terminatingFlowIds.push(reader.fixed64());
                            break;
                        }
                    case 4: {
                            if (!(message.debugAnnotations && message.debugAnnotations.length))
                                message.debugAnnotations = [];
                            message.debugAnnotations.push($root.perfetto.protos.DebugAnnotation.decode(reader, reader.uint32()));
                            break;
                        }
                    case 33: {
                            message.sourceLocation = $root.perfetto.protos.SourceLocation.decode(reader, reader.uint32());
                            break;
                        }
                    case 34: {
                            message.sourceLocationIid = reader.uint64();
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a TrackEvent message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.TrackEvent} TrackEvent
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            TrackEvent.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a TrackEvent message.
             * @function verify
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            TrackEvent.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                let properties = {};
                if (message.categoryIids != null && message.hasOwnProperty("categoryIids")) {
                    if (!Array.isArray(message.categoryIids))
                        return "categoryIids: array expected";
                    for (let i = 0; i < message.categoryIids.length; ++i)
                        if (!$util.isInteger(message.categoryIids[i]) && !(message.categoryIids[i] && $util.isInteger(message.categoryIids[i].low) && $util.isInteger(message.categoryIids[i].high)))
                            return "categoryIids: integer|Long[] expected";
                }
                if (message.categories != null && message.hasOwnProperty("categories")) {
                    if (!Array.isArray(message.categories))
                        return "categories: array expected";
                    for (let i = 0; i < message.categories.length; ++i)
                        if (!$util.isString(message.categories[i]))
                            return "categories: string[] expected";
                }
                if (message.nameIid != null && message.hasOwnProperty("nameIid")) {
                    properties.nameField = 1;
                    if (!$util.isInteger(message.nameIid) && !(message.nameIid && $util.isInteger(message.nameIid.low) && $util.isInteger(message.nameIid.high)))
                        return "nameIid: integer|Long expected";
                }
                if (message.name != null && message.hasOwnProperty("name")) {
                    if (properties.nameField === 1)
                        return "nameField: multiple values";
                    properties.nameField = 1;
                    if (!$util.isString(message.name))
                        return "name: string expected";
                }
                if (message.type != null && message.hasOwnProperty("type"))
                    switch (message.type) {
                    default:
                        return "type: enum value expected";
                    case 0:
                    case 1:
                    case 2:
                    case 3:
                    case 4:
                        break;
                    }
                if (message.trackUuid != null && message.hasOwnProperty("trackUuid"))
                    if (!$util.isInteger(message.trackUuid) && !(message.trackUuid && $util.isInteger(message.trackUuid.low) && $util.isInteger(message.trackUuid.high)))
                        return "trackUuid: integer|Long expected";
                if (message.counterValue != null && message.hasOwnProperty("counterValue")) {
                    properties.counterValueField = 1;
                    if (!$util.isInteger(message.counterValue) && !(message.counterValue && $util.isInteger(message.counterValue.low) && $util.isInteger(message.counterValue.high)))
                        return "counterValue: integer|Long expected";
                }
                if (message.doubleCounterValue != null && message.hasOwnProperty("doubleCounterValue")) {
                    if (properties.counterValueField === 1)
                        return "counterValueField: multiple values";
                    properties.counterValueField = 1;
                    if (typeof message.doubleCounterValue !== "number")
                        return "doubleCounterValue: number expected";
                }
                if (message.extraCounterTrackUuids != null && message.hasOwnProperty("extraCounterTrackUuids")) {
                    if (!Array.isArray(message.extraCounterTrackUuids))
                        return "extraCounterTrackUuids: array expected";
                    for (let i = 0; i < message.extraCounterTrackUuids.length; ++i)
                        if (!$util.isInteger(message.extraCounterTrackUuids[i]) && !(message.extraCounterTrackUuids[i] && $util.isInteger(message.extraCounterTrackUuids[i].low) && $util.isInteger(message.extraCounterTrackUuids[i].high)))
                            return "extraCounterTrackUuids: integer|Long[] expected";
                }
                if (message.extraCounterValues != null && message.hasOwnProperty("extraCounterValues")) {
                    if (!Array.isArray(message.extraCounterValues))
                        return "extraCounterValues: array expected";
                    for (let i = 0; i < message.extraCounterValues.length; ++i)
                        if (!$util.isInteger(message.extraCounterValues[i]) && !(message.extraCounterValues[i] && $util.isInteger(message.extraCounterValues[i].low) && $util.isInteger(message.extraCounterValues[i].high)))
                            return "extraCounterValues: integer|Long[] expected";
                }
                if (message.extraDoubleCounterTrackUuids != null && message.hasOwnProperty("extraDoubleCounterTrackUuids")) {
                    if (!Array.isArray(message.extraDoubleCounterTrackUuids))
                        return "extraDoubleCounterTrackUuids: array expected";
                    for (let i = 0; i < message.extraDoubleCounterTrackUuids.length; ++i)
                        if (!$util.isInteger(message.extraDoubleCounterTrackUuids[i]) && !(message.extraDoubleCounterTrackUuids[i] && $util.isInteger(message.extraDoubleCounterTrackUuids[i].low) && $util.isInteger(message.extraDoubleCounterTrackUuids[i].high)))
                            return "extraDoubleCounterTrackUuids: integer|Long[] expected";
                }
                if (message.extraDoubleCounterValues != null && message.hasOwnProperty("extraDoubleCounterValues")) {
                    if (!Array.isArray(message.extraDoubleCounterValues))
                        return "extraDoubleCounterValues: array expected";
                    for (let i = 0; i < message.extraDoubleCounterValues.length; ++i)
                        if (typeof message.extraDoubleCounterValues[i] !== "number")
                            return "extraDoubleCounterValues: number[] expected";
                }
                if (message.flowIdsOld != null && message.hasOwnProperty("flowIdsOld")) {
                    if (!Array.isArray(message.flowIdsOld))
                        return "flowIdsOld: array expected";
                    for (let i = 0; i < message.flowIdsOld.length; ++i)
                        if (!$util.isInteger(message.flowIdsOld[i]) && !(message.flowIdsOld[i] && $util.isInteger(message.flowIdsOld[i].low) && $util.isInteger(message.flowIdsOld[i].high)))
                            return "flowIdsOld: integer|Long[] expected";
                }
                if (message.flowIds != null && message.hasOwnProperty("flowIds")) {
                    if (!Array.isArray(message.flowIds))
                        return "flowIds: array expected";
                    for (let i = 0; i < message.flowIds.length; ++i)
                        if (!$util.isInteger(message.flowIds[i]) && !(message.flowIds[i] && $util.isInteger(message.flowIds[i].low) && $util.isInteger(message.flowIds[i].high)))
                            return "flowIds: integer|Long[] expected";
                }
                if (message.terminatingFlowIdsOld != null && message.hasOwnProperty("terminatingFlowIdsOld")) {
                    if (!Array.isArray(message.terminatingFlowIdsOld))
                        return "terminatingFlowIdsOld: array expected";
                    for (let i = 0; i < message.terminatingFlowIdsOld.length; ++i)
                        if (!$util.isInteger(message.terminatingFlowIdsOld[i]) && !(message.terminatingFlowIdsOld[i] && $util.isInteger(message.terminatingFlowIdsOld[i].low) && $util.isInteger(message.terminatingFlowIdsOld[i].high)))
                            return "terminatingFlowIdsOld: integer|Long[] expected";
                }
                if (message.terminatingFlowIds != null && message.hasOwnProperty("terminatingFlowIds")) {
                    if (!Array.isArray(message.terminatingFlowIds))
                        return "terminatingFlowIds: array expected";
                    for (let i = 0; i < message.terminatingFlowIds.length; ++i)
                        if (!$util.isInteger(message.terminatingFlowIds[i]) && !(message.terminatingFlowIds[i] && $util.isInteger(message.terminatingFlowIds[i].low) && $util.isInteger(message.terminatingFlowIds[i].high)))
                            return "terminatingFlowIds: integer|Long[] expected";
                }
                if (message.debugAnnotations != null && message.hasOwnProperty("debugAnnotations")) {
                    if (!Array.isArray(message.debugAnnotations))
                        return "debugAnnotations: array expected";
                    for (let i = 0; i < message.debugAnnotations.length; ++i) {
                        let error = $root.perfetto.protos.DebugAnnotation.verify(message.debugAnnotations[i]);
                        if (error)
                            return "debugAnnotations." + error;
                    }
                }
                if (message.sourceLocation != null && message.hasOwnProperty("sourceLocation")) {
                    properties.sourceLocationField = 1;
                    {
                        let error = $root.perfetto.protos.SourceLocation.verify(message.sourceLocation);
                        if (error)
                            return "sourceLocation." + error;
                    }
                }
                if (message.sourceLocationIid != null && message.hasOwnProperty("sourceLocationIid")) {
                    if (properties.sourceLocationField === 1)
                        return "sourceLocationField: multiple values";
                    properties.sourceLocationField = 1;
                    if (!$util.isInteger(message.sourceLocationIid) && !(message.sourceLocationIid && $util.isInteger(message.sourceLocationIid.low) && $util.isInteger(message.sourceLocationIid.high)))
                        return "sourceLocationIid: integer|Long expected";
                }
                return null;
            };

            /**
             * Creates a TrackEvent message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.TrackEvent} TrackEvent
             */
            TrackEvent.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.TrackEvent)
                    return object;
                let message = new $root.perfetto.protos.TrackEvent();
                if (object.categoryIids) {
                    if (!Array.isArray(object.categoryIids))
                        throw TypeError(".perfetto.protos.TrackEvent.categoryIids: array expected");
                    message.categoryIids = [];
                    for (let i = 0; i < object.categoryIids.length; ++i)
                        if ($util.Long)
                            (message.categoryIids[i] = $util.Long.fromValue(object.categoryIids[i])).unsigned = true;
                        else if (typeof object.categoryIids[i] === "string")
                            message.categoryIids[i] = parseInt(object.categoryIids[i], 10);
                        else if (typeof object.categoryIids[i] === "number")
                            message.categoryIids[i] = object.categoryIids[i];
                        else if (typeof object.categoryIids[i] === "object")
                            message.categoryIids[i] = new $util.LongBits(object.categoryIids[i].low >>> 0, object.categoryIids[i].high >>> 0).toNumber(true);
                }
                if (object.categories) {
                    if (!Array.isArray(object.categories))
                        throw TypeError(".perfetto.protos.TrackEvent.categories: array expected");
                    message.categories = [];
                    for (let i = 0; i < object.categories.length; ++i)
                        message.categories[i] = String(object.categories[i]);
                }
                if (object.nameIid != null)
                    if ($util.Long)
                        (message.nameIid = $util.Long.fromValue(object.nameIid)).unsigned = true;
                    else if (typeof object.nameIid === "string")
                        message.nameIid = parseInt(object.nameIid, 10);
                    else if (typeof object.nameIid === "number")
                        message.nameIid = object.nameIid;
                    else if (typeof object.nameIid === "object")
                        message.nameIid = new $util.LongBits(object.nameIid.low >>> 0, object.nameIid.high >>> 0).toNumber(true);
                if (object.name != null)
                    message.name = String(object.name);
                switch (object.type) {
                default:
                    if (typeof object.type === "number") {
                        message.type = object.type;
                        break;
                    }
                    break;
                case "TYPE_UNSPECIFIED":
                case 0:
                    message.type = 0;
                    break;
                case "TYPE_SLICE_BEGIN":
                case 1:
                    message.type = 1;
                    break;
                case "TYPE_SLICE_END":
                case 2:
                    message.type = 2;
                    break;
                case "TYPE_INSTANT":
                case 3:
                    message.type = 3;
                    break;
                case "TYPE_COUNTER":
                case 4:
                    message.type = 4;
                    break;
                }
                if (object.trackUuid != null)
                    if ($util.Long)
                        (message.trackUuid = $util.Long.fromValue(object.trackUuid)).unsigned = true;
                    else if (typeof object.trackUuid === "string")
                        message.trackUuid = parseInt(object.trackUuid, 10);
                    else if (typeof object.trackUuid === "number")
                        message.trackUuid = object.trackUuid;
                    else if (typeof object.trackUuid === "object")
                        message.trackUuid = new $util.LongBits(object.trackUuid.low >>> 0, object.trackUuid.high >>> 0).toNumber(true);
                if (object.counterValue != null)
                    if ($util.Long)
                        (message.counterValue = $util.Long.fromValue(object.counterValue)).unsigned = false;
                    else if (typeof object.counterValue === "string")
                        message.counterValue = parseInt(object.counterValue, 10);
                    else if (typeof object.counterValue === "number")
                        message.counterValue = object.counterValue;
                    else if (typeof object.counterValue === "object")
                        message.counterValue = new $util.LongBits(object.counterValue.low >>> 0, object.counterValue.high >>> 0).toNumber();
                if (object.doubleCounterValue != null)
                    message.doubleCounterValue = Number(object.doubleCounterValue);
                if (object.extraCounterTrackUuids) {
                    if (!Array.isArray(object.extraCounterTrackUuids))
                        throw TypeError(".perfetto.protos.TrackEvent.extraCounterTrackUuids: array expected");
                    message.extraCounterTrackUuids = [];
                    for (let i = 0; i < object.extraCounterTrackUuids.length; ++i)
                        if ($util.Long)
                            (message.extraCounterTrackUuids[i] = $util.Long.fromValue(object.extraCounterTrackUuids[i])).unsigned = true;
                        else if (typeof object.extraCounterTrackUuids[i] === "string")
                            message.extraCounterTrackUuids[i] = parseInt(object.extraCounterTrackUuids[i], 10);
                        else if (typeof object.extraCounterTrackUuids[i] === "number")
                            message.extraCounterTrackUuids[i] = object.extraCounterTrackUuids[i];
                        else if (typeof object.extraCounterTrackUuids[i] === "object")
                            message.extraCounterTrackUuids[i] = new $util.LongBits(object.extraCounterTrackUuids[i].low >>> 0, object.extraCounterTrackUuids[i].high >>> 0).toNumber(true);
                }
                if (object.extraCounterValues) {
                    if (!Array.isArray(object.extraCounterValues))
                        throw TypeError(".perfetto.protos.TrackEvent.extraCounterValues: array expected");
                    message.extraCounterValues = [];
                    for (let i = 0; i < object.extraCounterValues.length; ++i)
                        if ($util.Long)
                            (message.extraCounterValues[i] = $util.Long.fromValue(object.extraCounterValues[i])).unsigned = false;
                        else if (typeof object.extraCounterValues[i] === "string")
                            message.extraCounterValues[i] = parseInt(object.extraCounterValues[i], 10);
                        else if (typeof object.extraCounterValues[i] === "number")
                            message.extraCounterValues[i] = object.extraCounterValues[i];
                        else if (typeof object.extraCounterValues[i] === "object")
                            message.extraCounterValues[i] = new $util.LongBits(object.extraCounterValues[i].low >>> 0, object.extraCounterValues[i].high >>> 0).toNumber();
                }
                if (object.extraDoubleCounterTrackUuids) {
                    if (!Array.isArray(object.extraDoubleCounterTrackUuids))
                        throw TypeError(".perfetto.protos.TrackEvent.extraDoubleCounterTrackUuids: array expected");
                    message.extraDoubleCounterTrackUuids = [];
                    for (let i = 0; i < object.extraDoubleCounterTrackUuids.length; ++i)
                        if ($util.Long)
                            (message.extraDoubleCounterTrackUuids[i] = $util.Long.fromValue(object.extraDoubleCounterTrackUuids[i])).unsigned = true;
                        else if (typeof object.extraDoubleCounterTrackUuids[i] === "string")
                            message.extraDoubleCounterTrackUuids[i] = parseInt(object.extraDoubleCounterTrackUuids[i], 10);
                        else if (typeof object.extraDoubleCounterTrackUuids[i] === "number")
                            message.extraDoubleCounterTrackUuids[i] = object.extraDoubleCounterTrackUuids[i];
                        else if (typeof object.extraDoubleCounterTrackUuids[i] === "object")
                            message.extraDoubleCounterTrackUuids[i] = new $util.LongBits(object.extraDoubleCounterTrackUuids[i].low >>> 0, object.extraDoubleCounterTrackUuids[i].high >>> 0).toNumber(true);
                }
                if (object.extraDoubleCounterValues) {
                    if (!Array.isArray(object.extraDoubleCounterValues))
                        throw TypeError(".perfetto.protos.TrackEvent.extraDoubleCounterValues: array expected");
                    message.extraDoubleCounterValues = [];
                    for (let i = 0; i < object.extraDoubleCounterValues.length; ++i)
                        message.extraDoubleCounterValues[i] = Number(object.extraDoubleCounterValues[i]);
                }
                if (object.flowIdsOld) {
                    if (!Array.isArray(object.flowIdsOld))
                        throw TypeError(".perfetto.protos.TrackEvent.flowIdsOld: array expected");
                    message.flowIdsOld = [];
                    for (let i = 0; i < object.flowIdsOld.length; ++i)
                        if ($util.Long)
                            (message.flowIdsOld[i] = $util.Long.fromValue(object.flowIdsOld[i])).unsigned = true;
                        else if (typeof object.flowIdsOld[i] === "string")
                            message.flowIdsOld[i] = parseInt(object.flowIdsOld[i], 10);
                        else if (typeof object.flowIdsOld[i] === "number")
                            message.flowIdsOld[i] = object.flowIdsOld[i];
                        else if (typeof object.flowIdsOld[i] === "object")
                            message.flowIdsOld[i] = new $util.LongBits(object.flowIdsOld[i].low >>> 0, object.flowIdsOld[i].high >>> 0).toNumber(true);
                }
                if (object.flowIds) {
                    if (!Array.isArray(object.flowIds))
                        throw TypeError(".perfetto.protos.TrackEvent.flowIds: array expected");
                    message.flowIds = [];
                    for (let i = 0; i < object.flowIds.length; ++i)
                        if ($util.Long)
                            (message.flowIds[i] = $util.Long.fromValue(object.flowIds[i])).unsigned = false;
                        else if (typeof object.flowIds[i] === "string")
                            message.flowIds[i] = parseInt(object.flowIds[i], 10);
                        else if (typeof object.flowIds[i] === "number")
                            message.flowIds[i] = object.flowIds[i];
                        else if (typeof object.flowIds[i] === "object")
                            message.flowIds[i] = new $util.LongBits(object.flowIds[i].low >>> 0, object.flowIds[i].high >>> 0).toNumber();
                }
                if (object.terminatingFlowIdsOld) {
                    if (!Array.isArray(object.terminatingFlowIdsOld))
                        throw TypeError(".perfetto.protos.TrackEvent.terminatingFlowIdsOld: array expected");
                    message.terminatingFlowIdsOld = [];
                    for (let i = 0; i < object.terminatingFlowIdsOld.length; ++i)
                        if ($util.Long)
                            (message.terminatingFlowIdsOld[i] = $util.Long.fromValue(object.terminatingFlowIdsOld[i])).unsigned = true;
                        else if (typeof object.terminatingFlowIdsOld[i] === "string")
                            message.terminatingFlowIdsOld[i] = parseInt(object.terminatingFlowIdsOld[i], 10);
                        else if (typeof object.terminatingFlowIdsOld[i] === "number")
                            message.terminatingFlowIdsOld[i] = object.terminatingFlowIdsOld[i];
                        else if (typeof object.terminatingFlowIdsOld[i] === "object")
                            message.terminatingFlowIdsOld[i] = new $util.LongBits(object.terminatingFlowIdsOld[i].low >>> 0, object.terminatingFlowIdsOld[i].high >>> 0).toNumber(true);
                }
                if (object.terminatingFlowIds) {
                    if (!Array.isArray(object.terminatingFlowIds))
                        throw TypeError(".perfetto.protos.TrackEvent.terminatingFlowIds: array expected");
                    message.terminatingFlowIds = [];
                    for (let i = 0; i < object.terminatingFlowIds.length; ++i)
                        if ($util.Long)
                            (message.terminatingFlowIds[i] = $util.Long.fromValue(object.terminatingFlowIds[i])).unsigned = false;
                        else if (typeof object.terminatingFlowIds[i] === "string")
                            message.terminatingFlowIds[i] = parseInt(object.terminatingFlowIds[i], 10);
                        else if (typeof object.terminatingFlowIds[i] === "number")
                            message.terminatingFlowIds[i] = object.terminatingFlowIds[i];
                        else if (typeof object.terminatingFlowIds[i] === "object")
                            message.terminatingFlowIds[i] = new $util.LongBits(object.terminatingFlowIds[i].low >>> 0, object.terminatingFlowIds[i].high >>> 0).toNumber();
                }
                if (object.debugAnnotations) {
                    if (!Array.isArray(object.debugAnnotations))
                        throw TypeError(".perfetto.protos.TrackEvent.debugAnnotations: array expected");
                    message.debugAnnotations = [];
                    for (let i = 0; i < object.debugAnnotations.length; ++i) {
                        if (typeof object.debugAnnotations[i] !== "object")
                            throw TypeError(".perfetto.protos.TrackEvent.debugAnnotations: object expected");
                        message.debugAnnotations[i] = $root.perfetto.protos.DebugAnnotation.fromObject(object.debugAnnotations[i]);
                    }
                }
                if (object.sourceLocation != null) {
                    if (typeof object.sourceLocation !== "object")
                        throw TypeError(".perfetto.protos.TrackEvent.sourceLocation: object expected");
                    message.sourceLocation = $root.perfetto.protos.SourceLocation.fromObject(object.sourceLocation);
                }
                if (object.sourceLocationIid != null)
                    if ($util.Long)
                        (message.sourceLocationIid = $util.Long.fromValue(object.sourceLocationIid)).unsigned = true;
                    else if (typeof object.sourceLocationIid === "string")
                        message.sourceLocationIid = parseInt(object.sourceLocationIid, 10);
                    else if (typeof object.sourceLocationIid === "number")
                        message.sourceLocationIid = object.sourceLocationIid;
                    else if (typeof object.sourceLocationIid === "object")
                        message.sourceLocationIid = new $util.LongBits(object.sourceLocationIid.low >>> 0, object.sourceLocationIid.high >>> 0).toNumber(true);
                return message;
            };

            /**
             * Creates a plain object from a TrackEvent message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {perfetto.protos.TrackEvent} message TrackEvent
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            TrackEvent.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.arrays || options.defaults) {
                    object.categoryIids = [];
                    object.debugAnnotations = [];
                    object.extraCounterValues = [];
                    object.categories = [];
                    object.extraCounterTrackUuids = [];
                    object.flowIdsOld = [];
                    object.terminatingFlowIdsOld = [];
                    object.extraDoubleCounterTrackUuids = [];
                    object.extraDoubleCounterValues = [];
                    object.flowIds = [];
                    object.terminatingFlowIds = [];
                }
                if (options.defaults) {
                    object.type = options.enums === String ? "TYPE_UNSPECIFIED" : 0;
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.trackUuid = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.trackUuid = options.longs === String ? "0" : 0;
                }
                if (message.categoryIids && message.categoryIids.length) {
                    object.categoryIids = [];
                    for (let j = 0; j < message.categoryIids.length; ++j)
                        if (typeof message.categoryIids[j] === "number")
                            object.categoryIids[j] = options.longs === String ? String(message.categoryIids[j]) : message.categoryIids[j];
                        else
                            object.categoryIids[j] = options.longs === String ? $util.Long.prototype.toString.call(message.categoryIids[j]) : options.longs === Number ? new $util.LongBits(message.categoryIids[j].low >>> 0, message.categoryIids[j].high >>> 0).toNumber(true) : message.categoryIids[j];
                }
                if (message.debugAnnotations && message.debugAnnotations.length) {
                    object.debugAnnotations = [];
                    for (let j = 0; j < message.debugAnnotations.length; ++j)
                        object.debugAnnotations[j] = $root.perfetto.protos.DebugAnnotation.toObject(message.debugAnnotations[j], options);
                }
                if (message.type != null && message.hasOwnProperty("type"))
                    object.type = options.enums === String ? $root.perfetto.protos.TrackEvent.Type[message.type] === undefined ? message.type : $root.perfetto.protos.TrackEvent.Type[message.type] : message.type;
                if (message.nameIid != null && message.hasOwnProperty("nameIid")) {
                    if (typeof message.nameIid === "number")
                        object.nameIid = options.longs === String ? String(message.nameIid) : message.nameIid;
                    else
                        object.nameIid = options.longs === String ? $util.Long.prototype.toString.call(message.nameIid) : options.longs === Number ? new $util.LongBits(message.nameIid.low >>> 0, message.nameIid.high >>> 0).toNumber(true) : message.nameIid;
                    if (options.oneofs)
                        object.nameField = "nameIid";
                }
                if (message.trackUuid != null && message.hasOwnProperty("trackUuid"))
                    if (typeof message.trackUuid === "number")
                        object.trackUuid = options.longs === String ? String(message.trackUuid) : message.trackUuid;
                    else
                        object.trackUuid = options.longs === String ? $util.Long.prototype.toString.call(message.trackUuid) : options.longs === Number ? new $util.LongBits(message.trackUuid.low >>> 0, message.trackUuid.high >>> 0).toNumber(true) : message.trackUuid;
                if (message.extraCounterValues && message.extraCounterValues.length) {
                    object.extraCounterValues = [];
                    for (let j = 0; j < message.extraCounterValues.length; ++j)
                        if (typeof message.extraCounterValues[j] === "number")
                            object.extraCounterValues[j] = options.longs === String ? String(message.extraCounterValues[j]) : message.extraCounterValues[j];
                        else
                            object.extraCounterValues[j] = options.longs === String ? $util.Long.prototype.toString.call(message.extraCounterValues[j]) : options.longs === Number ? new $util.LongBits(message.extraCounterValues[j].low >>> 0, message.extraCounterValues[j].high >>> 0).toNumber() : message.extraCounterValues[j];
                }
                if (message.categories && message.categories.length) {
                    object.categories = [];
                    for (let j = 0; j < message.categories.length; ++j)
                        object.categories[j] = message.categories[j];
                }
                if (message.name != null && message.hasOwnProperty("name")) {
                    object.name = message.name;
                    if (options.oneofs)
                        object.nameField = "name";
                }
                if (message.counterValue != null && message.hasOwnProperty("counterValue")) {
                    if (typeof message.counterValue === "number")
                        object.counterValue = options.longs === String ? String(message.counterValue) : message.counterValue;
                    else
                        object.counterValue = options.longs === String ? $util.Long.prototype.toString.call(message.counterValue) : options.longs === Number ? new $util.LongBits(message.counterValue.low >>> 0, message.counterValue.high >>> 0).toNumber() : message.counterValue;
                    if (options.oneofs)
                        object.counterValueField = "counterValue";
                }
                if (message.extraCounterTrackUuids && message.extraCounterTrackUuids.length) {
                    object.extraCounterTrackUuids = [];
                    for (let j = 0; j < message.extraCounterTrackUuids.length; ++j)
                        if (typeof message.extraCounterTrackUuids[j] === "number")
                            object.extraCounterTrackUuids[j] = options.longs === String ? String(message.extraCounterTrackUuids[j]) : message.extraCounterTrackUuids[j];
                        else
                            object.extraCounterTrackUuids[j] = options.longs === String ? $util.Long.prototype.toString.call(message.extraCounterTrackUuids[j]) : options.longs === Number ? new $util.LongBits(message.extraCounterTrackUuids[j].low >>> 0, message.extraCounterTrackUuids[j].high >>> 0).toNumber(true) : message.extraCounterTrackUuids[j];
                }
                if (message.sourceLocation != null && message.hasOwnProperty("sourceLocation")) {
                    object.sourceLocation = $root.perfetto.protos.SourceLocation.toObject(message.sourceLocation, options);
                    if (options.oneofs)
                        object.sourceLocationField = "sourceLocation";
                }
                if (message.sourceLocationIid != null && message.hasOwnProperty("sourceLocationIid")) {
                    if (typeof message.sourceLocationIid === "number")
                        object.sourceLocationIid = options.longs === String ? String(message.sourceLocationIid) : message.sourceLocationIid;
                    else
                        object.sourceLocationIid = options.longs === String ? $util.Long.prototype.toString.call(message.sourceLocationIid) : options.longs === Number ? new $util.LongBits(message.sourceLocationIid.low >>> 0, message.sourceLocationIid.high >>> 0).toNumber(true) : message.sourceLocationIid;
                    if (options.oneofs)
                        object.sourceLocationField = "sourceLocationIid";
                }
                if (message.flowIdsOld && message.flowIdsOld.length) {
                    object.flowIdsOld = [];
                    for (let j = 0; j < message.flowIdsOld.length; ++j)
                        if (typeof message.flowIdsOld[j] === "number")
                            object.flowIdsOld[j] = options.longs === String ? String(message.flowIdsOld[j]) : message.flowIdsOld[j];
                        else
                            object.flowIdsOld[j] = options.longs === String ? $util.Long.prototype.toString.call(message.flowIdsOld[j]) : options.longs === Number ? new $util.LongBits(message.flowIdsOld[j].low >>> 0, message.flowIdsOld[j].high >>> 0).toNumber(true) : message.flowIdsOld[j];
                }
                if (message.terminatingFlowIdsOld && message.terminatingFlowIdsOld.length) {
                    object.terminatingFlowIdsOld = [];
                    for (let j = 0; j < message.terminatingFlowIdsOld.length; ++j)
                        if (typeof message.terminatingFlowIdsOld[j] === "number")
                            object.terminatingFlowIdsOld[j] = options.longs === String ? String(message.terminatingFlowIdsOld[j]) : message.terminatingFlowIdsOld[j];
                        else
                            object.terminatingFlowIdsOld[j] = options.longs === String ? $util.Long.prototype.toString.call(message.terminatingFlowIdsOld[j]) : options.longs === Number ? new $util.LongBits(message.terminatingFlowIdsOld[j].low >>> 0, message.terminatingFlowIdsOld[j].high >>> 0).toNumber(true) : message.terminatingFlowIdsOld[j];
                }
                if (message.doubleCounterValue != null && message.hasOwnProperty("doubleCounterValue")) {
                    object.doubleCounterValue = options.json && !isFinite(message.doubleCounterValue) ? String(message.doubleCounterValue) : message.doubleCounterValue;
                    if (options.oneofs)
                        object.counterValueField = "doubleCounterValue";
                }
                if (message.extraDoubleCounterTrackUuids && message.extraDoubleCounterTrackUuids.length) {
                    object.extraDoubleCounterTrackUuids = [];
                    for (let j = 0; j < message.extraDoubleCounterTrackUuids.length; ++j)
                        if (typeof message.extraDoubleCounterTrackUuids[j] === "number")
                            object.extraDoubleCounterTrackUuids[j] = options.longs === String ? String(message.extraDoubleCounterTrackUuids[j]) : message.extraDoubleCounterTrackUuids[j];
                        else
                            object.extraDoubleCounterTrackUuids[j] = options.longs === String ? $util.Long.prototype.toString.call(message.extraDoubleCounterTrackUuids[j]) : options.longs === Number ? new $util.LongBits(message.extraDoubleCounterTrackUuids[j].low >>> 0, message.extraDoubleCounterTrackUuids[j].high >>> 0).toNumber(true) : message.extraDoubleCounterTrackUuids[j];
                }
                if (message.extraDoubleCounterValues && message.extraDoubleCounterValues.length) {
                    object.extraDoubleCounterValues = [];
                    for (let j = 0; j < message.extraDoubleCounterValues.length; ++j)
                        object.extraDoubleCounterValues[j] = options.json && !isFinite(message.extraDoubleCounterValues[j]) ? String(message.extraDoubleCounterValues[j]) : message.extraDoubleCounterValues[j];
                }
                if (message.flowIds && message.flowIds.length) {
                    object.flowIds = [];
                    for (let j = 0; j < message.flowIds.length; ++j)
                        if (typeof message.flowIds[j] === "number")
                            object.flowIds[j] = options.longs === String ? String(message.flowIds[j]) : message.flowIds[j];
                        else
                            object.flowIds[j] = options.longs === String ? $util.Long.prototype.toString.call(message.flowIds[j]) : options.longs === Number ? new $util.LongBits(message.flowIds[j].low >>> 0, message.flowIds[j].high >>> 0).toNumber() : message.flowIds[j];
                }
                if (message.terminatingFlowIds && message.terminatingFlowIds.length) {
                    object.terminatingFlowIds = [];
                    for (let j = 0; j < message.terminatingFlowIds.length; ++j)
                        if (typeof message.terminatingFlowIds[j] === "number")
                            object.terminatingFlowIds[j] = options.longs === String ? String(message.terminatingFlowIds[j]) : message.terminatingFlowIds[j];
                        else
                            object.terminatingFlowIds[j] = options.longs === String ? $util.Long.prototype.toString.call(message.terminatingFlowIds[j]) : options.longs === Number ? new $util.LongBits(message.terminatingFlowIds[j].low >>> 0, message.terminatingFlowIds[j].high >>> 0).toNumber() : message.terminatingFlowIds[j];
                }
                return object;
            };

            /**
             * Converts this TrackEvent to JSON.
             * @function toJSON
             * @memberof perfetto.protos.TrackEvent
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            TrackEvent.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for TrackEvent
             * @function getTypeUrl
             * @memberof perfetto.protos.TrackEvent
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            TrackEvent.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.TrackEvent";
            };

            /**
             * Type enum.
             * @name perfetto.protos.TrackEvent.Type
             * @enum {number}
             * @property {number} TYPE_UNSPECIFIED=0 TYPE_UNSPECIFIED value
             * @property {number} TYPE_SLICE_BEGIN=1 TYPE_SLICE_BEGIN value
             * @property {number} TYPE_SLICE_END=2 TYPE_SLICE_END value
             * @property {number} TYPE_INSTANT=3 TYPE_INSTANT value
             * @property {number} TYPE_COUNTER=4 TYPE_COUNTER value
             */
            TrackEvent.Type = (function() {
                const valuesById = {}, values = Object.create(valuesById);
                values[valuesById[0] = "TYPE_UNSPECIFIED"] = 0;
                values[valuesById[1] = "TYPE_SLICE_BEGIN"] = 1;
                values[valuesById[2] = "TYPE_SLICE_END"] = 2;
                values[valuesById[3] = "TYPE_INSTANT"] = 3;
                values[valuesById[4] = "TYPE_COUNTER"] = 4;
                return values;
            })();

            return TrackEvent;
        })();

        protos.TracePacket = (function() {

            /**
             * Properties of a TracePacket.
             * @memberof perfetto.protos
             * @interface ITracePacket
             * @property {number|Long|null} [timestamp] TracePacket timestamp
             * @property {number|null} [timestampClockId] TracePacket timestampClockId
             * @property {perfetto.protos.ITrackEvent|null} [trackEvent] TracePacket trackEvent
             * @property {perfetto.protos.ITrackDescriptor|null} [trackDescriptor] TracePacket trackDescriptor
             * @property {perfetto.protos.IInternedData|null} [internedData] TracePacket internedData
             * @property {number|null} [sequenceFlags] TracePacket sequenceFlags
             * @property {number|null} [trustedUid] TracePacket trustedUid
             * @property {number|null} [trustedPacketSequenceId] TracePacket trustedPacketSequenceId
             * @property {number|null} [trustedPid] TracePacket trustedPid
             * @property {boolean|null} [previousPacketDropped] TracePacket previousPacketDropped
             * @property {boolean|null} [firstPacketOnSequence] TracePacket firstPacketOnSequence
             */

            /**
             * Constructs a new TracePacket.
             * @memberof perfetto.protos
             * @classdesc Represents a TracePacket.
             * @implements ITracePacket
             * @constructor
             * @param {perfetto.protos.ITracePacket=} [properties] Properties to set
             */
            function TracePacket(properties) {
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * TracePacket timestamp.
             * @member {number|Long} timestamp
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.timestamp = $util.Long ? $util.Long.fromBits(0,0,true) : 0;

            /**
             * TracePacket timestampClockId.
             * @member {number} timestampClockId
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.timestampClockId = 0;

            /**
             * TracePacket trackEvent.
             * @member {perfetto.protos.ITrackEvent|null|undefined} trackEvent
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.trackEvent = null;

            /**
             * TracePacket trackDescriptor.
             * @member {perfetto.protos.ITrackDescriptor|null|undefined} trackDescriptor
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.trackDescriptor = null;

            /**
             * TracePacket internedData.
             * @member {perfetto.protos.IInternedData|null|undefined} internedData
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.internedData = null;

            /**
             * TracePacket sequenceFlags.
             * @member {number} sequenceFlags
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.sequenceFlags = 0;

            /**
             * TracePacket trustedUid.
             * @member {number|null|undefined} trustedUid
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.trustedUid = null;

            /**
             * TracePacket trustedPacketSequenceId.
             * @member {number|null|undefined} trustedPacketSequenceId
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.trustedPacketSequenceId = null;

            /**
             * TracePacket trustedPid.
             * @member {number} trustedPid
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.trustedPid = 0;

            /**
             * TracePacket previousPacketDropped.
             * @member {boolean} previousPacketDropped
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.previousPacketDropped = false;

            /**
             * TracePacket firstPacketOnSequence.
             * @member {boolean} firstPacketOnSequence
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            TracePacket.prototype.firstPacketOnSequence = false;

            // OneOf field names bound to virtual getters and setters
            let $oneOfFields;

            /**
             * TracePacket data.
             * @member {"trackEvent"|"trackDescriptor"|undefined} data
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            Object.defineProperty(TracePacket.prototype, "data", {
                get: $util.oneOfGetter($oneOfFields = ["trackEvent", "trackDescriptor"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * TracePacket optionalTrustedUid.
             * @member {"trustedUid"|undefined} optionalTrustedUid
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            Object.defineProperty(TracePacket.prototype, "optionalTrustedUid", {
                get: $util.oneOfGetter($oneOfFields = ["trustedUid"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * TracePacket optionalTrustedPacketSequenceId.
             * @member {"trustedPacketSequenceId"|undefined} optionalTrustedPacketSequenceId
             * @memberof perfetto.protos.TracePacket
             * @instance
             */
            Object.defineProperty(TracePacket.prototype, "optionalTrustedPacketSequenceId", {
                get: $util.oneOfGetter($oneOfFields = ["trustedPacketSequenceId"]),
                set: $util.oneOfSetter($oneOfFields)
            });

            /**
             * Creates a new TracePacket instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {perfetto.protos.ITracePacket=} [properties] Properties to set
             * @returns {perfetto.protos.TracePacket} TracePacket instance
             */
            TracePacket.create = function create(properties) {
                return new TracePacket(properties);
            };

            /**
             * Encodes the specified TracePacket message. Does not implicitly {@link perfetto.protos.TracePacket.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {perfetto.protos.ITracePacket} message TracePacket message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            TracePacket.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.trustedUid != null && Object.hasOwnProperty.call(message, "trustedUid"))
                    writer.uint32(/* id 3, wireType 0 =*/24).int32(message.trustedUid);
                if (message.timestamp != null && Object.hasOwnProperty.call(message, "timestamp"))
                    writer.uint32(/* id 8, wireType 0 =*/64).uint64(message.timestamp);
                if (message.trustedPacketSequenceId != null && Object.hasOwnProperty.call(message, "trustedPacketSequenceId"))
                    writer.uint32(/* id 10, wireType 0 =*/80).uint32(message.trustedPacketSequenceId);
                if (message.trackEvent != null && Object.hasOwnProperty.call(message, "trackEvent"))
                    $root.perfetto.protos.TrackEvent.encode(message.trackEvent, writer.uint32(/* id 11, wireType 2 =*/90).fork()).ldelim();
                if (message.internedData != null && Object.hasOwnProperty.call(message, "internedData"))
                    $root.perfetto.protos.InternedData.encode(message.internedData, writer.uint32(/* id 12, wireType 2 =*/98).fork()).ldelim();
                if (message.sequenceFlags != null && Object.hasOwnProperty.call(message, "sequenceFlags"))
                    writer.uint32(/* id 13, wireType 0 =*/104).uint32(message.sequenceFlags);
                if (message.previousPacketDropped != null && Object.hasOwnProperty.call(message, "previousPacketDropped"))
                    writer.uint32(/* id 42, wireType 0 =*/336).bool(message.previousPacketDropped);
                if (message.timestampClockId != null && Object.hasOwnProperty.call(message, "timestampClockId"))
                    writer.uint32(/* id 58, wireType 0 =*/464).uint32(message.timestampClockId);
                if (message.trackDescriptor != null && Object.hasOwnProperty.call(message, "trackDescriptor"))
                    $root.perfetto.protos.TrackDescriptor.encode(message.trackDescriptor, writer.uint32(/* id 60, wireType 2 =*/482).fork()).ldelim();
                if (message.trustedPid != null && Object.hasOwnProperty.call(message, "trustedPid"))
                    writer.uint32(/* id 79, wireType 0 =*/632).int32(message.trustedPid);
                if (message.firstPacketOnSequence != null && Object.hasOwnProperty.call(message, "firstPacketOnSequence"))
                    writer.uint32(/* id 87, wireType 0 =*/696).bool(message.firstPacketOnSequence);
                return writer;
            };

            /**
             * Encodes the specified TracePacket message, length delimited. Does not implicitly {@link perfetto.protos.TracePacket.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {perfetto.protos.ITracePacket} message TracePacket message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            TracePacket.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a TracePacket message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.TracePacket} TracePacket
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            TracePacket.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.TracePacket();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 8: {
                            message.timestamp = reader.uint64();
                            break;
                        }
                    case 58: {
                            message.timestampClockId = reader.uint32();
                            break;
                        }
                    case 11: {
                            message.trackEvent = $root.perfetto.protos.TrackEvent.decode(reader, reader.uint32());
                            break;
                        }
                    case 60: {
                            message.trackDescriptor = $root.perfetto.protos.TrackDescriptor.decode(reader, reader.uint32());
                            break;
                        }
                    case 12: {
                            message.internedData = $root.perfetto.protos.InternedData.decode(reader, reader.uint32());
                            break;
                        }
                    case 13: {
                            message.sequenceFlags = reader.uint32();
                            break;
                        }
                    case 3: {
                            message.trustedUid = reader.int32();
                            break;
                        }
                    case 10: {
                            message.trustedPacketSequenceId = reader.uint32();
                            break;
                        }
                    case 79: {
                            message.trustedPid = reader.int32();
                            break;
                        }
                    case 42: {
                            message.previousPacketDropped = reader.bool();
                            break;
                        }
                    case 87: {
                            message.firstPacketOnSequence = reader.bool();
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a TracePacket message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.TracePacket} TracePacket
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            TracePacket.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a TracePacket message.
             * @function verify
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            TracePacket.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                let properties = {};
                if (message.timestamp != null && message.hasOwnProperty("timestamp"))
                    if (!$util.isInteger(message.timestamp) && !(message.timestamp && $util.isInteger(message.timestamp.low) && $util.isInteger(message.timestamp.high)))
                        return "timestamp: integer|Long expected";
                if (message.timestampClockId != null && message.hasOwnProperty("timestampClockId"))
                    if (!$util.isInteger(message.timestampClockId))
                        return "timestampClockId: integer expected";
                if (message.trackEvent != null && message.hasOwnProperty("trackEvent")) {
                    properties.data = 1;
                    {
                        let error = $root.perfetto.protos.TrackEvent.verify(message.trackEvent);
                        if (error)
                            return "trackEvent." + error;
                    }
                }
                if (message.trackDescriptor != null && message.hasOwnProperty("trackDescriptor")) {
                    if (properties.data === 1)
                        return "data: multiple values";
                    properties.data = 1;
                    {
                        let error = $root.perfetto.protos.TrackDescriptor.verify(message.trackDescriptor);
                        if (error)
                            return "trackDescriptor." + error;
                    }
                }
                if (message.internedData != null && message.hasOwnProperty("internedData")) {
                    let error = $root.perfetto.protos.InternedData.verify(message.internedData);
                    if (error)
                        return "internedData." + error;
                }
                if (message.sequenceFlags != null && message.hasOwnProperty("sequenceFlags"))
                    if (!$util.isInteger(message.sequenceFlags))
                        return "sequenceFlags: integer expected";
                if (message.trustedUid != null && message.hasOwnProperty("trustedUid")) {
                    properties.optionalTrustedUid = 1;
                    if (!$util.isInteger(message.trustedUid))
                        return "trustedUid: integer expected";
                }
                if (message.trustedPacketSequenceId != null && message.hasOwnProperty("trustedPacketSequenceId")) {
                    properties.optionalTrustedPacketSequenceId = 1;
                    if (!$util.isInteger(message.trustedPacketSequenceId))
                        return "trustedPacketSequenceId: integer expected";
                }
                if (message.trustedPid != null && message.hasOwnProperty("trustedPid"))
                    if (!$util.isInteger(message.trustedPid))
                        return "trustedPid: integer expected";
                if (message.previousPacketDropped != null && message.hasOwnProperty("previousPacketDropped"))
                    if (typeof message.previousPacketDropped !== "boolean")
                        return "previousPacketDropped: boolean expected";
                if (message.firstPacketOnSequence != null && message.hasOwnProperty("firstPacketOnSequence"))
                    if (typeof message.firstPacketOnSequence !== "boolean")
                        return "firstPacketOnSequence: boolean expected";
                return null;
            };

            /**
             * Creates a TracePacket message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.TracePacket} TracePacket
             */
            TracePacket.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.TracePacket)
                    return object;
                let message = new $root.perfetto.protos.TracePacket();
                if (object.timestamp != null)
                    if ($util.Long)
                        (message.timestamp = $util.Long.fromValue(object.timestamp)).unsigned = true;
                    else if (typeof object.timestamp === "string")
                        message.timestamp = parseInt(object.timestamp, 10);
                    else if (typeof object.timestamp === "number")
                        message.timestamp = object.timestamp;
                    else if (typeof object.timestamp === "object")
                        message.timestamp = new $util.LongBits(object.timestamp.low >>> 0, object.timestamp.high >>> 0).toNumber(true);
                if (object.timestampClockId != null)
                    message.timestampClockId = object.timestampClockId >>> 0;
                if (object.trackEvent != null) {
                    if (typeof object.trackEvent !== "object")
                        throw TypeError(".perfetto.protos.TracePacket.trackEvent: object expected");
                    message.trackEvent = $root.perfetto.protos.TrackEvent.fromObject(object.trackEvent);
                }
                if (object.trackDescriptor != null) {
                    if (typeof object.trackDescriptor !== "object")
                        throw TypeError(".perfetto.protos.TracePacket.trackDescriptor: object expected");
                    message.trackDescriptor = $root.perfetto.protos.TrackDescriptor.fromObject(object.trackDescriptor);
                }
                if (object.internedData != null) {
                    if (typeof object.internedData !== "object")
                        throw TypeError(".perfetto.protos.TracePacket.internedData: object expected");
                    message.internedData = $root.perfetto.protos.InternedData.fromObject(object.internedData);
                }
                if (object.sequenceFlags != null)
                    message.sequenceFlags = object.sequenceFlags >>> 0;
                if (object.trustedUid != null)
                    message.trustedUid = object.trustedUid | 0;
                if (object.trustedPacketSequenceId != null)
                    message.trustedPacketSequenceId = object.trustedPacketSequenceId >>> 0;
                if (object.trustedPid != null)
                    message.trustedPid = object.trustedPid | 0;
                if (object.previousPacketDropped != null)
                    message.previousPacketDropped = Boolean(object.previousPacketDropped);
                if (object.firstPacketOnSequence != null)
                    message.firstPacketOnSequence = Boolean(object.firstPacketOnSequence);
                return message;
            };

            /**
             * Creates a plain object from a TracePacket message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {perfetto.protos.TracePacket} message TracePacket
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            TracePacket.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.defaults) {
                    if ($util.Long) {
                        let long = new $util.Long(0, 0, true);
                        object.timestamp = options.longs === String ? long.toString() : options.longs === Number ? long.toNumber() : long;
                    } else
                        object.timestamp = options.longs === String ? "0" : 0;
                    object.internedData = null;
                    object.sequenceFlags = 0;
                    object.previousPacketDropped = false;
                    object.timestampClockId = 0;
                    object.trustedPid = 0;
                    object.firstPacketOnSequence = false;
                }
                if (message.trustedUid != null && message.hasOwnProperty("trustedUid")) {
                    object.trustedUid = message.trustedUid;
                    if (options.oneofs)
                        object.optionalTrustedUid = "trustedUid";
                }
                if (message.timestamp != null && message.hasOwnProperty("timestamp"))
                    if (typeof message.timestamp === "number")
                        object.timestamp = options.longs === String ? String(message.timestamp) : message.timestamp;
                    else
                        object.timestamp = options.longs === String ? $util.Long.prototype.toString.call(message.timestamp) : options.longs === Number ? new $util.LongBits(message.timestamp.low >>> 0, message.timestamp.high >>> 0).toNumber(true) : message.timestamp;
                if (message.trustedPacketSequenceId != null && message.hasOwnProperty("trustedPacketSequenceId")) {
                    object.trustedPacketSequenceId = message.trustedPacketSequenceId;
                    if (options.oneofs)
                        object.optionalTrustedPacketSequenceId = "trustedPacketSequenceId";
                }
                if (message.trackEvent != null && message.hasOwnProperty("trackEvent")) {
                    object.trackEvent = $root.perfetto.protos.TrackEvent.toObject(message.trackEvent, options);
                    if (options.oneofs)
                        object.data = "trackEvent";
                }
                if (message.internedData != null && message.hasOwnProperty("internedData"))
                    object.internedData = $root.perfetto.protos.InternedData.toObject(message.internedData, options);
                if (message.sequenceFlags != null && message.hasOwnProperty("sequenceFlags"))
                    object.sequenceFlags = message.sequenceFlags;
                if (message.previousPacketDropped != null && message.hasOwnProperty("previousPacketDropped"))
                    object.previousPacketDropped = message.previousPacketDropped;
                if (message.timestampClockId != null && message.hasOwnProperty("timestampClockId"))
                    object.timestampClockId = message.timestampClockId;
                if (message.trackDescriptor != null && message.hasOwnProperty("trackDescriptor")) {
                    object.trackDescriptor = $root.perfetto.protos.TrackDescriptor.toObject(message.trackDescriptor, options);
                    if (options.oneofs)
                        object.data = "trackDescriptor";
                }
                if (message.trustedPid != null && message.hasOwnProperty("trustedPid"))
                    object.trustedPid = message.trustedPid;
                if (message.firstPacketOnSequence != null && message.hasOwnProperty("firstPacketOnSequence"))
                    object.firstPacketOnSequence = message.firstPacketOnSequence;
                return object;
            };

            /**
             * Converts this TracePacket to JSON.
             * @function toJSON
             * @memberof perfetto.protos.TracePacket
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            TracePacket.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for TracePacket
             * @function getTypeUrl
             * @memberof perfetto.protos.TracePacket
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            TracePacket.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.TracePacket";
            };

            /**
             * SequenceFlags enum.
             * @name perfetto.protos.TracePacket.SequenceFlags
             * @enum {number}
             * @property {number} SEQ_UNSPECIFIED=0 SEQ_UNSPECIFIED value
             * @property {number} SEQ_INCREMENTAL_STATE_CLEARED=1 SEQ_INCREMENTAL_STATE_CLEARED value
             * @property {number} SEQ_NEEDS_INCREMENTAL_STATE=2 SEQ_NEEDS_INCREMENTAL_STATE value
             */
            TracePacket.SequenceFlags = (function() {
                const valuesById = {}, values = Object.create(valuesById);
                values[valuesById[0] = "SEQ_UNSPECIFIED"] = 0;
                values[valuesById[1] = "SEQ_INCREMENTAL_STATE_CLEARED"] = 1;
                values[valuesById[2] = "SEQ_NEEDS_INCREMENTAL_STATE"] = 2;
                return values;
            })();

            return TracePacket;
        })();

        protos.Trace = (function() {

            /**
             * Properties of a Trace.
             * @memberof perfetto.protos
             * @interface ITrace
             * @property {Array.<perfetto.protos.ITracePacket>|null} [packet] Trace packet
             */

            /**
             * Constructs a new Trace.
             * @memberof perfetto.protos
             * @classdesc Represents a Trace.
             * @implements ITrace
             * @constructor
             * @param {perfetto.protos.ITrace=} [properties] Properties to set
             */
            function Trace(properties) {
                this.packet = [];
                if (properties)
                    for (let keys = Object.keys(properties), i = 0; i < keys.length; ++i)
                        if (properties[keys[i]] != null)
                            this[keys[i]] = properties[keys[i]];
            }

            /**
             * Trace packet.
             * @member {Array.<perfetto.protos.ITracePacket>} packet
             * @memberof perfetto.protos.Trace
             * @instance
             */
            Trace.prototype.packet = $util.emptyArray;

            /**
             * Creates a new Trace instance using the specified properties.
             * @function create
             * @memberof perfetto.protos.Trace
             * @static
             * @param {perfetto.protos.ITrace=} [properties] Properties to set
             * @returns {perfetto.protos.Trace} Trace instance
             */
            Trace.create = function create(properties) {
                return new Trace(properties);
            };

            /**
             * Encodes the specified Trace message. Does not implicitly {@link perfetto.protos.Trace.verify|verify} messages.
             * @function encode
             * @memberof perfetto.protos.Trace
             * @static
             * @param {perfetto.protos.ITrace} message Trace message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            Trace.encode = function encode(message, writer) {
                if (!writer)
                    writer = $Writer.create();
                if (message.packet != null && message.packet.length)
                    for (let i = 0; i < message.packet.length; ++i)
                        $root.perfetto.protos.TracePacket.encode(message.packet[i], writer.uint32(/* id 1, wireType 2 =*/10).fork()).ldelim();
                return writer;
            };

            /**
             * Encodes the specified Trace message, length delimited. Does not implicitly {@link perfetto.protos.Trace.verify|verify} messages.
             * @function encodeDelimited
             * @memberof perfetto.protos.Trace
             * @static
             * @param {perfetto.protos.ITrace} message Trace message or plain object to encode
             * @param {$protobuf.Writer} [writer] Writer to encode to
             * @returns {$protobuf.Writer} Writer
             */
            Trace.encodeDelimited = function encodeDelimited(message, writer) {
                return this.encode(message, writer).ldelim();
            };

            /**
             * Decodes a Trace message from the specified reader or buffer.
             * @function decode
             * @memberof perfetto.protos.Trace
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @param {number} [length] Message length if known beforehand
             * @returns {perfetto.protos.Trace} Trace
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            Trace.decode = function decode(reader, length, error) {
                if (!(reader instanceof $Reader))
                    reader = $Reader.create(reader);
                let end = length === undefined ? reader.len : reader.pos + length, message = new $root.perfetto.protos.Trace();
                while (reader.pos < end) {
                    let tag = reader.uint32();
                    if (tag === error)
                        break;
                    switch (tag >>> 3) {
                    case 1: {
                            if (!(message.packet && message.packet.length))
                                message.packet = [];
                            message.packet.push($root.perfetto.protos.TracePacket.decode(reader, reader.uint32()));
                            break;
                        }
                    default:
                        reader.skipType(tag & 7);
                        break;
                    }
                }
                return message;
            };

            /**
             * Decodes a Trace message from the specified reader or buffer, length delimited.
             * @function decodeDelimited
             * @memberof perfetto.protos.Trace
             * @static
             * @param {$protobuf.Reader|Uint8Array} reader Reader or buffer to decode from
             * @returns {perfetto.protos.Trace} Trace
             * @throws {Error} If the payload is not a reader or valid buffer
             * @throws {$protobuf.util.ProtocolError} If required fields are missing
             */
            Trace.decodeDelimited = function decodeDelimited(reader) {
                if (!(reader instanceof $Reader))
                    reader = new $Reader(reader);
                return this.decode(reader, reader.uint32());
            };

            /**
             * Verifies a Trace message.
             * @function verify
             * @memberof perfetto.protos.Trace
             * @static
             * @param {Object.<string,*>} message Plain object to verify
             * @returns {string|null} `null` if valid, otherwise the reason why it is not
             */
            Trace.verify = function verify(message) {
                if (typeof message !== "object" || message === null)
                    return "object expected";
                if (message.packet != null && message.hasOwnProperty("packet")) {
                    if (!Array.isArray(message.packet))
                        return "packet: array expected";
                    for (let i = 0; i < message.packet.length; ++i) {
                        let error = $root.perfetto.protos.TracePacket.verify(message.packet[i]);
                        if (error)
                            return "packet." + error;
                    }
                }
                return null;
            };

            /**
             * Creates a Trace message from a plain object. Also converts values to their respective internal types.
             * @function fromObject
             * @memberof perfetto.protos.Trace
             * @static
             * @param {Object.<string,*>} object Plain object
             * @returns {perfetto.protos.Trace} Trace
             */
            Trace.fromObject = function fromObject(object) {
                if (object instanceof $root.perfetto.protos.Trace)
                    return object;
                let message = new $root.perfetto.protos.Trace();
                if (object.packet) {
                    if (!Array.isArray(object.packet))
                        throw TypeError(".perfetto.protos.Trace.packet: array expected");
                    message.packet = [];
                    for (let i = 0; i < object.packet.length; ++i) {
                        if (typeof object.packet[i] !== "object")
                            throw TypeError(".perfetto.protos.Trace.packet: object expected");
                        message.packet[i] = $root.perfetto.protos.TracePacket.fromObject(object.packet[i]);
                    }
                }
                return message;
            };

            /**
             * Creates a plain object from a Trace message. Also converts values to other types if specified.
             * @function toObject
             * @memberof perfetto.protos.Trace
             * @static
             * @param {perfetto.protos.Trace} message Trace
             * @param {$protobuf.IConversionOptions} [options] Conversion options
             * @returns {Object.<string,*>} Plain object
             */
            Trace.toObject = function toObject(message, options) {
                if (!options)
                    options = {};
                let object = {};
                if (options.arrays || options.defaults)
                    object.packet = [];
                if (message.packet && message.packet.length) {
                    object.packet = [];
                    for (let j = 0; j < message.packet.length; ++j)
                        object.packet[j] = $root.perfetto.protos.TracePacket.toObject(message.packet[j], options);
                }
                return object;
            };

            /**
             * Converts this Trace to JSON.
             * @function toJSON
             * @memberof perfetto.protos.Trace
             * @instance
             * @returns {Object.<string,*>} JSON object
             */
            Trace.prototype.toJSON = function toJSON() {
                return this.constructor.toObject(this, $protobuf.util.toJSONOptions);
            };

            /**
             * Gets the default type url for Trace
             * @function getTypeUrl
             * @memberof perfetto.protos.Trace
             * @static
             * @param {string} [typeUrlPrefix] your custom typeUrlPrefix(default "type.googleapis.com")
             * @returns {string} The default type url
             */
            Trace.getTypeUrl = function getTypeUrl(typeUrlPrefix) {
                if (typeUrlPrefix === undefined) {
                    typeUrlPrefix = "type.googleapis.com";
                }
                return typeUrlPrefix + "/perfetto.protos.Trace";
            };

            return Trace;
        })();

        return protos;
    })();

    return perfetto;
})();

export { $root as default };
