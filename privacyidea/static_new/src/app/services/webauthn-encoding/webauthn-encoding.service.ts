import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class WebauthnEncodingService {
  constructor() {}

  /**
   * Encodes a Uint8Array into a web-safe base64 string.
   * This format (Base64URL) replaces '+' with '-', '/' with '_', and removes padding.
   * @param data The Uint8Array to encode.
   * @returns The web-safe base64 encoded string.
   */
  public encodeWebAuthnBase64(data: Uint8Array): string {
    // Convert Uint8Array to a binary string (each byte becomes a character code)
    let binaryString = '';
    data.forEach((byte) => {
      binaryString += String.fromCharCode(byte);
    });

    // Use btoa for standard base64 encoding
    const base64 = btoa(binaryString);

    // Make it web-safe (Base64URL):
    // 1. Replace '+' with '-'
    // 2. Replace '/' with '_'
    // 3. Remove padding '=' characters from the end
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  /**
   * Encodes a JavaScript object into a web-safe base64 string.
   * The object is first stringified to JSON, then encoded to UTF-8,
   * and finally encoded using web-safe base64.
   * @param data The JavaScript object to encode.
   * @returns The web-safe base64 encoded string.
   */
  public encodeWebAuthnJson(data: any): string {
    const jsonString = JSON.stringify(data);
    // Convert the JSON string to a Uint8Array using UTF-8 encoding
    const utf8Bytes = new TextEncoder().encode(jsonString);
    // Encode the UTF-8 bytes using web-safe base64
    return this.encodeWebAuthnBase64(utf8Bytes);
  }
}
