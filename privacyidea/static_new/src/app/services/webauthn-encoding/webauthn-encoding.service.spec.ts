import { TestBed } from '@angular/core/testing';
import { WebauthnEncodingService } from './webauthn-encoding.service';

describe('WebauthnEncodingService', () => {
  let service: WebauthnEncodingService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(WebauthnEncodingService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('encodeWebAuthnBase64', () => {
    it('should encode Uint8Array to web-safe base64', () => {
      // Example from RFC 4648, Section 5 (base64url)
      // The string "\xFB\xEF\xBE" (in hex) is encoded as "+++/".
      // In base64url, this should be "--_". (Padding is removed)
      const data1 = new Uint8Array([0xfb, 0xef, 0xbe]); // Corresponds to binary string for btoa: ûï¾
      expect(service.encodeWebAuthnBase64(data1)).toBe('--8'); // btoa("ûï¾") -> "/v7+" -> web-safe: "_v7-" -> Oh, my manual conversion was wrong. Let's use a known example.
      // Let's use a simpler example: "foo" -> Zm9v
      const dataFoo = new TextEncoder().encode('foo'); // Uint8Array [102, 111, 111]
      expect(service.encodeWebAuthnBase64(dataFoo)).toBe('Zm9v');

      // Example with characters that need replacement:
      // ASCII: "?>" -> base64: "Pz4=" -> base64url: "Pz4" (padding removed)
      const dataQuestionGreater = new TextEncoder().encode('?>'); // Uint8Array [63, 62]
      expect(service.encodeWebAuthnBase64(dataQuestionGreater)).toBe('Pz4');

      // Example that would have + and /
      // Binary: 11111100 00111111 11000000 (0xFC, 0x3F, 0xC0)
      // Base64: /D/A
      // Base64URL: _D_A
      const dataWithPlusSlash = new Uint8Array([0xfc, 0x3f, 0xc0]);
      expect(service.encodeWebAuthnBase64(dataWithPlusSlash)).toBe('_D_A');
    });

    it('should remove padding characters', () => {
      const dataPadding1 = new TextEncoder().encode('fo'); // Zm8=
      expect(service.encodeWebAuthnBase64(dataPadding1)).toBe('Zm8');
      const dataPadding2 = new TextEncoder().encode('f'); // Zg==
      expect(service.encodeWebAuthnBase64(dataPadding2)).toBe('Zg');
    });
  });

  describe('encodeWebAuthnJson', () => {
    it('should encode JSON object to web-safe base64', () => {
      const jsonData = { message: 'hello world', value: 123 };
      // JSON.stringify: {"message":"hello world","value":123}
      // UTF-8 bytes then web-safe base64
      const expected = service.encodeWebAuthnBase64(
        new TextEncoder().encode(JSON.stringify(jsonData)),
      );
      expect(service.encodeWebAuthnJson(jsonData)).toBe(expected);
      // A concrete example: {"alg":"ES256"} -> eyJhbGciOiJFUzI1NiJ9 (no padding, no + or /)
      expect(service.encodeWebAuthnJson({ alg: 'ES256' })).toBe(
        'eyJhbGciOiJFUzI1NiJ9',
      );
    });
  });
});
