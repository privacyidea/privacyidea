export interface EnrollmentResponse<D extends EnrollmentResponseDetail = EnrollmentResponseDetail> {
  detail: D;

  [key: string]: any;
}

export interface EnrollmentResponseDetail {
  serial: string;
  rollout_state?: string;
  threadid?: number;
  passkey_registration?: any;
  u2fRegisterRequest?: any;
  pushurl?: EnrollmentUrl;
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
  realm: string;
  onlyAddToRealm?: boolean;
  pin: string;
  serial: string | null;
  [key: string]: any; // TODO: remove this when all types are defined
};

export interface TokenEnrollmentPayload {
  type: string;
  description?: string;
  container_serial?: string;
  validity_period_start?: string;
  validity_period_end?: string;
  user?: string | null;
  realm?: string | null;
  pin?: string;
}

export interface TokenApiPayloadMapper<T> {
  toApiPayload(data: T): any;

  fromApiPayload(data: any): T;
}
