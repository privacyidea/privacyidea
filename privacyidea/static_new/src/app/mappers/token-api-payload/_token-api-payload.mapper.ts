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
