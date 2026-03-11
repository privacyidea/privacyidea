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

import { ComponentFixture, TestBed } from "@angular/core/testing";
import { TokenService } from "../../../../services/token/token.service";
import { ContentService } from "../../../../services/content/content.service";
import { MockTokenService } from "src/testing/mock-services/mock-token-service";
import { MockContentService } from "src/testing/mock-services/mock-content-service";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { NO_ERRORS_SCHEMA } from "@angular/core";

import { TokenCompleteEnrollmentComponent } from "./token-complete-enrollment.component";
import { of } from "rxjs";

describe("TokenCompleteEnrollmentComponent", () => {
  let component: TokenCompleteEnrollmentComponent;
  let fixture: ComponentFixture<TokenCompleteEnrollmentComponent>;
  let dialogRefSpy: { close: jest.Mock };
  let mockTokenService: MockTokenService;

  const dialogData = {
    response: { detail: { serial: "123" }, type: "hotp" },
    enrollParameters: { data: { type: "hotp", twoStepInit: true } }
  };

  beforeEach(async () => {
    dialogRefSpy = { close: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [TokenCompleteEnrollmentComponent],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: dialogData }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenCompleteEnrollmentComponent);
    component = fixture.componentInstance;
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should disable enroll action if input is invalid", () => {
    component.clientPartControl.setValue("");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(true);
    expect(component.dialogActions()[0].disabled).toBe(true);
  });

  it("should enable enroll action if input is valid", () => {
    component.clientPartControl.setValue("SOMEKEY");
    fixture.detectChanges();
    expect(component.invalidInputSignal()).toBe(false);
    expect(component.dialogActions()[0].disabled).toBe(false);
  });

  it("should call enrollToken and close dialog on successful enroll", () => {
    mockTokenService.enrollToken = jest.fn().mockReturnValue(of({
      detail: { serial: "X", rollout_state: "enrolled" },
      result: { status: true }
    } as any));
    component.clientPartControl.setValue("SOMEKEY");
    component.onDialogAction("enroll");
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).toHaveBeenCalled();
  });

  it("should not close dialog if rollout_state is client_wait", () => {
     mockTokenService.enrollToken = jest.fn().mockReturnValue(of({
      detail: { serial: "X", rollout_state: "client_wait" },
      result: { status: true }
    } as any));
    component.clientPartControl.setValue("SOMEKEY");
    component.onDialogAction("enroll");
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(dialogRefSpy.close).not.toHaveBeenCalled();
  });

  it('should remove twoStepInit from enrollParameters.data when enrolling', () => {
    component.clientPartControl.setValue('SOMEKEY');
    fixture.detectChanges();
    jest.spyOn(component['tokenService'], 'enrollToken').mockImplementation((params) => {
      expect(params.data.type).toEqual("hotp");
      expect(params.data['twoStepInit']).toBeUndefined();
      return of({ result: { status: true }, detail: { rollout_state: 'enrolled', type: 'hotp', serial: '123' }, type: 'hotp' });
    });
    component.onDialogAction('enroll');
  });
});
