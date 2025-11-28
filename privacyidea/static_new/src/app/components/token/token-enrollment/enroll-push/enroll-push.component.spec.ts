/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { EnrollPushComponent } from "./enroll-push.component";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { EnrollmentResponse } from "../../../../mappers/token-api-payload/_token-api-payload.mapper";
import { PiResponse } from "../../../../app.component";
import { MockDialogService, MockTokenService } from "../../../../../testing/mock-services";
import { Tokens, TokenService } from "../../../../services/token/token.service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { PushApiPayloadMapper } from "../../../../mappers/token-api-payload/push-token-api-payload.mapper";
import { lastValueFrom, of, throwError } from "rxjs";
import { ReopenDialogFn } from "../token-enrollment.component";

function makeInitResp(serial = "S-1"): EnrollmentResponse {
  return {
    result: { status: true, value: true },
    detail: { serial } as any,
    type: "push"
  } as EnrollmentResponse;
}

function makePollResp(rollout_state: string): PiResponse<Tokens, unknown> {
  return {
    result: {
      status: true,
      value: {
        tokens: [{ rollout_state }],
        count: 1,
        current: 1
      } as any
    }
  } as any;
}

class DummyPushApiPayloadMapper {
  map(x: any) {
    return x;
  }
}

describe("EnrollPushComponent", () => {
  let fixture: ComponentFixture<EnrollPushComponent>;
  let component: EnrollPushComponent;
  let tokenSvc: jest.Mocked<MockTokenService>;
  let dialogSvc: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollPushComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PushApiPayloadMapper, useClass: DummyPushApiPayloadMapper }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(EnrollPushComponent);
    component = fixture.componentInstance;
    tokenSvc = TestBed.inject(TokenService) as unknown as jest.Mocked<MockTokenService>;
    dialogSvc = TestBed.inject(DialogService) as unknown as MockDialogService;
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("ngOnInit emits additionalFormFields and clickEnroll handler", () => {
    const addSpy = jest.spyOn(component.additionalFormFieldsChange, "emit");
    const clickSpy = jest.spyOn(component.enrollmentArgsGetterChange, "emit");

    component.ngOnInit();

    expect(addSpy).toHaveBeenCalledWith({});
    expect(clickSpy).toHaveBeenCalled();
    const emitted = clickSpy.mock.calls[0][0] as (opts: any) => Promise<EnrollmentResponse | null>;
    expect(typeof emitted).toBe("function");
  });

  it("enrolls, opens dialog, polls to done, closes dialog and returns initResp", async () => {
    const initResp = makeInitResp("S-1");
    const pollResp = makePollResp("done");

    tokenSvc.enrollToken.mockReturnValue(of(initResp) as any);
    tokenSvc.pollTokenRolloutState.mockReturnValue(of(pollResp) as any);

    const enrollmentArgs = component.enrollmentArgsGetter({} as any);
    const initResponse = await lastValueFrom(tokenSvc.enrollToken(enrollmentArgs));
    await component.onEnrollmentResponse(initResponse as EnrollmentResponse);

    expect(tokenSvc.enrollToken).toHaveBeenCalledTimes(1);
    expect(dialogSvc.openTokenEnrollmentFirstStepDialog).toHaveBeenCalledTimes(1);
    expect(tokenSvc.pollTokenRolloutState).toHaveBeenCalledTimes(1);
    expect(dialogSvc.closeTokenEnrollmentFirstStepDialog).toHaveBeenCalledTimes(1);
    expect(component.pollResponse()).toBeUndefined();
  });

  // Is now handled by generic token enrollment component
  //
  // it("returns null when enrollToken errors", async () => {
  //   tokenSvc.enrollToken.mockReturnValue(throwError(() => new Error("boom")) as any);

  //   const res = await component.enrollmentArgsGetter({} as any);

  //   expect(res).toBeNull();
  //   expect(dialogSvc.openTokenEnrollmentFirstStepDialog).not.toHaveBeenCalled();
  // });

  it("keeps dialog open when rollout_state is clientwait", async () => {
    tokenSvc.enrollToken.mockReturnValue(of(makeInitResp()) as any);
    tokenSvc.pollTokenRolloutState.mockReturnValue(of(makePollResp("clientwait")) as any);

    const enrollmentArgs = component.enrollmentArgsGetter({} as any);
    const initResponse = await lastValueFrom(tokenSvc.enrollToken(enrollmentArgs));
    await component.onEnrollmentResponse(initResponse as EnrollmentResponse);

    expect(initResponse).not.toBeNull();
    expect(dialogSvc.openTokenEnrollmentFirstStepDialog).toHaveBeenCalled();
    expect(dialogSvc.closeTokenEnrollmentFirstStepDialog).not.toHaveBeenCalled();
  });

  it("reopenDialogChange provides a Promise callback that re-triggers polling when dialog is not open", async () => {
    const initResp = makeInitResp("S-2");
    const pollResp = makePollResp("done");
    tokenSvc.enrollToken.mockReturnValue(of(initResp) as any);
    tokenSvc.pollTokenRolloutState.mockReturnValue(of(pollResp) as any);

    let reopenFn: ReopenDialogFn;
    component.reopenDialogChange.subscribe((fn) => (reopenFn = fn));

    const enrollmentArgs = component.enrollmentArgsGetter({} as any);
    const initResponse = await lastValueFrom(tokenSvc.enrollToken(enrollmentArgs));
    await component.onEnrollmentResponse(initResponse as EnrollmentResponse);

    expect(typeof reopenFn!).toBe("function");

    dialogSvc.isTokenEnrollmentFirstStepDialogOpen = true;
    const r1 = await reopenFn!();
    expect(r1).toBeNull();

    dialogSvc.isTokenEnrollmentFirstStepDialogOpen = false;
    const r2 = await reopenFn!();
    expect(r2).toEqual(initResp);
    expect(tokenSvc.pollTokenRolloutState).toHaveBeenCalledTimes(2);
  });

  it("stopPolling is invoked when dialog afterClosed emits", async () => {
    const initResp = makeInitResp("S-3");
    const pollResp = makePollResp("done");
    tokenSvc.enrollToken.mockReturnValue(of(initResp) as any);
    tokenSvc.pollTokenRolloutState.mockReturnValue(of(pollResp) as any);

    const enrollmentArgs = component.enrollmentArgsGetter({} as any);
    const initResponse = await lastValueFrom(tokenSvc.enrollToken(enrollmentArgs));
    await component.onEnrollmentResponse(initResponse as EnrollmentResponse);

    expect(tokenSvc.stopPolling).toHaveBeenCalled();
  });
});
