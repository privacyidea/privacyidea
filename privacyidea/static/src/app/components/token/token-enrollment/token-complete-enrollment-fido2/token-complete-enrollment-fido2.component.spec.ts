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
import { TokenCompleteEnrollmentFido2Component } from "./token-complete-enrollment-fido2.component";

const response = { result: { status: true }, detail: { serial: "WAN0001" } } as unknown as EnrollmentResponse;
const registered = { result: { status: true }, detail: { serial: "WAN0001" } } as unknown as EnrollmentResponse;

describe("TokenCompleteEnrollmentFido2Component", () => {
  let host: MockEnrollmentStepHost;
  let register: jest.Mock<Promise<EnrollmentStepResult>, [AbortSignal]>;

  const setup = async (...results: (EnrollmentStepResult | Error)[]) => {
    TestBed.resetTestingModule();
    // Without a result, the registration is still running.
    register = jest.fn<Promise<EnrollmentStepResult>, [AbortSignal]>(() => new Promise(() => undefined));
    for (const result of results) {
      register.mockImplementationOnce(() =>
        result instanceof Error ? Promise.reject(result) : Promise.resolve(result)
      );
    }
    host = mockEnrollmentStepHost({ tokenType: "webauthn", response }, { firstStep: { kind: "fido2", register } });
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

  it("finishes the step with the registered token", async () => {
    await setup(registered);

    expect(register).toHaveBeenCalledTimes(1);
    expect(host.flow.finishStep).toHaveBeenCalledWith(registered);
  });

  it("ends the enrollment once the registration deleted the token", async () => {
    await setup(ENROLLMENT_CANCELLED);

    expect(host.flow.finishStep).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
  });

  it("offers Retry after a failed attempt and registers again", async () => {
    const fixture = await setup(null, registered);
    const step = fixture.componentInstance;

    expect(host.flow.finishStep).not.toHaveBeenCalled();
    expect(text(fixture)).toContain("The registration was not completed. Please try again.");
    expect(step.actions().map((action) => action.value)).toEqual(["retry"]);

    step.onAction("retry");
    await settle();

    expect(register).toHaveBeenCalledTimes(2);
    expect(host.flow.finishStep).toHaveBeenCalledWith(registered);
  });

  it("treats an unexpected error like a failed attempt", async () => {
    const fixture = await setup(new Error("boom"));

    expect(fixture.componentInstance.actions().map((action) => action.value)).toEqual(["retry"]);
    expect(host.flow.finishStep).not.toHaveBeenCalled();
  });

  it("announces the failure to screen readers", async () => {
    const fixture = await setup(null);
    const failure = Array.from(fixture.nativeElement.querySelectorAll("p") as NodeListOf<HTMLElement>).find(
      (paragraph) => paragraph.textContent?.includes("not completed")
    );

    expect(failure?.closest("[aria-live='polite']")).toBeTruthy();
  });

  it("aborts the registration and ignores its result once the step is left", async () => {
    let resolve!: (result: EnrollmentStepResult) => void;
    TestBed.resetTestingModule();
    register = jest.fn<Promise<EnrollmentStepResult>, [AbortSignal]>(
      () => new Promise<EnrollmentStepResult>((done) => (resolve = done))
    );
    host = mockEnrollmentStepHost({ tokenType: "passkey", response }, { firstStep: { kind: "fido2", register } });
    TestBed.configureTestingModule({ imports: [TokenCompleteEnrollmentFido2Component], providers: [host.provider] });
    const fixture = TestBed.createComponent(TokenCompleteEnrollmentFido2Component);
    fixture.detectChanges();
    const signal = register.mock.calls[0][0];

    fixture.destroy();
    resolve(registered);
    await Promise.resolve();
    await Promise.resolve();

    expect(signal.aborted).toBe(true);
    expect(host.flow.finishStep).not.toHaveBeenCalled();
  });

  it("passes the axe accessibility checks", async () => {
    const fixture = await setup(null);

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
