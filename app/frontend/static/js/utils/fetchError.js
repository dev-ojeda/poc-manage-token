export class FetchError extends Error {
    constructor(message, code, raw) {
        super(message);
        this.name = "FetchError";
        this.code = code;
        this.raw = raw;
    }
}