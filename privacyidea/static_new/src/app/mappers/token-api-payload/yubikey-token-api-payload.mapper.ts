import {
  TokenApiPayloadMapper,
  TokenEnrollmentPayload,
  TokenEnrollmentData,
} from './_token-api-payload.mapper';

export interface YubikeyEnrollmentData extends TokenEnrollmentData {
  type: 'yubikey';
  otpKey: string | null;
  otpLength: number | null;
}
export interface YubikeyEnrollmentPayload extends TokenEnrollmentPayload {
  otpkey: string | null;
  otplen: number | null;
}

export class YubikeyApiPayloadMapper
  implements TokenApiPayloadMapper<YubikeyEnrollmentData>
{
  toApiPayload(data: YubikeyEnrollmentData): any {
    // Placeholder: Implement transformation to API payload. We will replace this later.
    return { ...data };
  }

  fromApiPayload(payload: any): YubikeyEnrollmentData {
    // Placeholder: Implement transformation from API payload. We will replace this later.
    return payload as YubikeyEnrollmentData;
  }
}
