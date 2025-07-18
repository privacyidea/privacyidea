import { Injectable } from '@angular/core';

export interface Base64ServiceInterface {
  base64URLToBytes(base64URL: string): Uint8Array;
  bytesToBase64(buffer: Uint8Array): string;
  bufferToBase64Url(buffer: Uint8Array): string;
}

@Injectable({
  providedIn: 'root',
})
export class Base64Service {
  constructor() {}

  base64URLToBytes(base64URL: string): Uint8Array {
    const padding = '='.repeat((4 - (base64URL.length % 4)) % 4);
    const base64 = (base64URL + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  bytesToBase64(buffer: Uint8Array): string {
    let binary = '';
    const len = buffer.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(buffer[i]);
    }
    return window.btoa(binary);
  }

  bufferToBase64Url(buffer: Uint8Array): string {
    const base64 = this.bytesToBase64(buffer);
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
}
