/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { TestBed } from "@angular/core/testing";
import { EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import {
  ENROLLMENT_CANCELLED,
  EnrollmentStepResult
} from "@components/token/token-enrollment/token-enrollment.constants";
import { axe } from "@testing/axe";
import { MockEnrollmentStepHost, mockEnrollmentStepHost } from "@testing/enrollment-step-host";
import { Observable, of } from "rxjs";
import { TokenCompleteEnrollmentFido2Component } from "./token-complete-enrollment-fido2.component";

type FinalRequest = Observable<EnrollmentStepResult>;

const response = { result: { status: true }, detail: { serial: "WAN0001" } } as unknown as EnrollmentResponse;
const registered = { result: { status: true }, detail: { serial: "WAN0001" } } as unknown as EnrollmentResponse;

describe("TokenCompleteEnrollmentFido2Component", () => {
  let host: MockEnrollmentStepHost;
  let register: jest.Mock<Promise<FinalRequest | null>, [AbortSignal]>;

  const setup = async (results: (FinalRequest | null | Error)[] = [], state: { sentInput?: string } = {}) => {
    TestBed.resetTestingModule();
    // Without a result, the browser registration is still running.
    register = jest.fn<Promise<FinalRequest | null>, [AbortSignal]>(() => new Promise(() => undefined));
    for (const result of results) {
      register.mockImplementationOnce(() =>
        result instanceof Error ? Promise.reject(result) : Promise.resolve(result)
      );
    }
    host = mockEnrollmentStepHost(
      { tokenType: "webauthn", response },
      { firstStep: { kind: "fido2", register }, ...state }
    );
    TestBed.configureTestingModule({ imports: [TokenCompleteEnrollmentFido2Component], providers: [host.provider] });
    const fixture = TestBed.createComponent(TokenCompleteEnrollmentFido2Component);
    fixture.detectChanges();
    await settle();
    fixture.detectChanges();
    return fixture;
  };

  // Lets the registration attempt finish.
  const settle = () => new Promise((resolve) => setTimeout(resolve));
  const text = (fixture: { nativeElement: HTMLElement }) => fixture.nativeElement.textContent ?? "";

  it("registers as an incomplete step and starts the registration at once", async () => {
    const fixture = await setup();
    const step = fixture.componentInstance;

    expect(host.register).toHaveBeenCalledWith(step);
    expect(step.title()).toBe("Take Action on Your Authenticator");
    expect(step.headerState).toBe("incomplete");
    expect(step.deleteWarning).toBeNull();
    expect(text(fixture)).toContain("You need to confirm the registration with your authenticator.");
    expect(step.actions()).toEqual([]);
  });

  it("lets the flow send the final request and passes its result on", async () => {
    const finalRequest = of(registered);
    await setup([finalRequest]);

    expect(register).toHaveBeenCalledTimes(1);
    const [request, toResult] = host.flow.sendStepRequest.mock.calls[0];
    expect(request).toBe(finalRequest);
    expect(toResult(registered)).toBe(registered);
    expect(toResult(ENROLLMENT_CANCELLED)).toBe(ENROLLMENT_CANCELLED);
    expect(toResult(null)).toBeNull();
  });

  it("offers Retry after a failed attempt and registers again", async () => {
    const finalRequest = of(registered);
    const fixture = await setup([null, finalRequest]);
    const step = fixture.componentInstance;

    expect(host.flow.sendStepRequest).not.toHaveBeenCalled();
    expect(text(fixture)).toContain("The registration was not completed. Please try again.");
    expect(step.actions().map((action) => action.value)).toEqual(["retry"]);

    step.onAction("retry");
    await settle();

    expect(register).toHaveBeenCalledTimes(2);
    expect(host.flow.sendStepRequest).toHaveBeenCalledWith(finalRequest, expect.any(Function));
  });

  it("treats an unexpected error like a failed attempt", async () => {
    const fixture = await setup([new Error("boom")]);

    expect(fixture.componentInstance.actions().map((action) => action.value)).toEqual(["retry"]);
    expect(host.flow.sendStepRequest).not.toHaveBeenCalled();
  });

  it("offers Retry once the final WebAuthn request failed", async () => {
    const fixture = await setup([of(null)]);

    host.flow.stepRequestFailed.set(true);
    fixture.detectChanges();

    expect(text(fixture)).toContain("The registration was not completed. Please try again.");
    expect(fixture.componentInstance.actions().map((action) => action.value)).toEqual(["retry"]);
  });

  it("waits for the final request instead of registering again when it is reopened while the request runs", async () => {
    const fixture = await setup([], { sentInput: "" });

    expect(register).not.toHaveBeenCalled();
    expect(text(fixture)).toContain("The registration is being completed. Please wait.");
    expect(fixture.componentInstance.actions()).toEqual([]);
  });

  it("announces the failure to screen readers", async () => {
    const fixture = await setup([null]);
    const failure = Array.from(fixture.nativeElement.querySelectorAll("p") as NodeListOf<HTMLElement>).find(
      (paragraph) => paragraph.textContent?.includes("not completed")
    );

    expect(failure?.closest("[aria-live='polite']")).toBeTruthy();
  });

  it("aborts the browser registration and sends no final request once the step is left", async () => {
    let resolve!: (result: FinalRequest | null) => void;
    TestBed.resetTestingModule();
    register = jest.fn<Promise<FinalRequest | null>, [AbortSignal]>(
      () => new Promise<FinalRequest | null>((done) => (resolve = done))
    );
    host = mockEnrollmentStepHost({ tokenType: "passkey", response }, { firstStep: { kind: "fido2", register } });
    TestBed.configureTestingModule({ imports: [TokenCompleteEnrollmentFido2Component], providers: [host.provider] });
    const fixture = TestBed.createComponent(TokenCompleteEnrollmentFido2Component);
    fixture.detectChanges();
    const signal = register.mock.calls[0][0];

    fixture.destroy();
    resolve(of(registered));
    await Promise.resolve();
    await Promise.resolve();

    expect(signal.aborted).toBe(true);
    expect(host.flow.sendStepRequest).not.toHaveBeenCalled();
  });

  it("passes the axe accessibility checks", async () => {
    const fixture = await setup([null]);

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
