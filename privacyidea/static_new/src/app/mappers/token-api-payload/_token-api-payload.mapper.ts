export interface EnrollmentResponse<
  D extends EnrollmentResponseDetail = EnrollmentResponseDetail,
> {
  detail: D;
  [key: string]: any;
}

export interface EnrollmentResponseDetail {
  rollout_state: string;
  serial: string;
  threadid?: number; // TODO: always, or only in Webauthn??
  passkey_registration?: any;
  u2fRegisterRequest?: any;
  pushurl?: EnrollmentUrl;
  transaction_id?: string;
  googleurl?: EnrollmentUrl;
  otpkey?: EnrollmentUrl;
  motpurl?: EnrollmentUrl;
  tiqrenroll?: EnrollmentUrl;
  [key: string]: any;
}

export interface EnrollmentUrl {
  description: string;
  img: string;
  value: string;
  value_b32?: string;
}

export type TokenEnrollmentData = {
  type: string;
  description: string;
  containerSerial: string;
  validityPeriodStart: string;
  validityPeriodEnd: string;
  user: string;
  pin: string;
  [key: string]: any; // TODO: remove this when all types are defined
};

export interface TokenEnrollmentPayload {
  type: string;
  description: string;
  container_serial: string;
  validity_period_start: string;
  validity_period_end: string;
  user: string | null; // User can be null for some types like 4eyes
  pin: string;
  // Other common fields can be added here if necessary
}

export interface TokenApiPayloadMapper<T> {
  toApiPayload(data: T): any;
  fromApiPayload(data: any): T;
}
