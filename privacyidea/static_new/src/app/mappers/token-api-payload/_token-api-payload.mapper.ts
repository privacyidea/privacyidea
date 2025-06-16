export type TokenEnrollmentData = {
  type: string;
  description: string;
  container_serial: string;
  validity_period_start: string;
  validity_period_end: string;
  user: string;
  pin: string;
  [key: string]: any; // TODO: remove this when all types are defined
};

export interface TokenApiPayloadMapper<T> {
  toApiPayload(data: T): any;
  fromApiPayload(data: any): T;
}
