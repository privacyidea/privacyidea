/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { HttpHeaders, HttpProgressEvent, HttpResourceRef } from "@angular/common/http";
import { Resource, ResourceStatus, Signal, signal, WritableSignal } from "@angular/core";

export function makeResource<T>(initial: T) {
  return {
    value: signal(initial) as WritableSignal<T>,
    reload: jest.fn(),
    error: jest.fn().mockReturnValue(null)
  };
}

export class MockHttpResourceRef<T> implements HttpResourceRef<T> {
  value: WritableSignal<T>;

  set(value: T): void {
    this.value.set(value);
  }

  update(updater: (value: T) => T): void {
    this.value.set(updater(this.value()));
  }

  asReadonly(): Resource<T> {
    return {
      value: this.value,
      reload: this.reload,
      error: this.error,
      hasValue: this.hasValue.bind(this),
      status: signal(ResourceStatus.Resolved),
      isLoading: signal(false)
    } as any;
  }

  headers: Signal<HttpHeaders | undefined> = signal(undefined);
  statusCode: Signal<number | undefined> = signal(undefined);
  progress: Signal<HttpProgressEvent | undefined> = signal(undefined);

  hasValue(): this is HttpResourceRef<Exclude<T, undefined>> {
    return this.value() !== undefined;
  }

  destroy(): void {}

  status: Signal<ResourceStatus> = signal(ResourceStatus.Resolved);
  error = signal<Error | null>(null);
  isLoading: Signal<boolean> = signal(false);
  reload = jest.fn();

  constructor(initial: T) {
    this.value = signal(initial) as WritableSignal<T>;
  }
}

export class MockBase64Service {
  base64URLToBytes = jest.fn((_: string) => new Uint8Array([1, 2]));
  bytesToBase64 = jest.fn(() => "b64");
}

export class MockPiResponse<Value, Detail = unknown> {
  error?: { code: number; message: string };
  id: number;
  jsonrpc: string;
  detail: Detail;
  result?: {
    authentication?: "CHALLENGE" | "POLL" | "PUSH";
    status: boolean;
    value?: Value;
    error?: { code: number; message: string };
  };
  signature: string;
  time: number;
  version: string;
  versionnumber: string;

  constructor(args: {
    detail?: Detail;
    result?: { authentication?: "CHALLENGE" | "POLL" | "PUSH"; status: boolean; value?: Value; error?: { code: number; message: string } };
    error?: { code: number; message: string };
    id?: number;
    jsonrpc?: string;
    signature?: string;
    time?: number;
    version?: string;
    versionnumber?: string;
  }) {
    this.detail = (args.detail ?? ({} as Detail));
    this.result = args.result;
    this.error = args.error;
    this.id = args.id ?? 0;
    this.jsonrpc = args.jsonrpc ?? "2.0";
    this.signature = args.signature ?? "";
    this.time = args.time ?? Date.now();
    this.version = args.version ?? "1.0";
    this.versionnumber = args.versionnumber ?? "1.0";
  }

  static fromValue<Value, Detail = unknown>(value: Value, detail: Detail = {} as Detail): MockPiResponse<Value, Detail> {
    return new MockPiResponse<Value, Detail>({ detail, result: { status: true, value } });
  }
}
