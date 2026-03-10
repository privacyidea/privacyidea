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
import { TokenEnrollmentLastStepDialogComponent } from "./token-enrollment-last-step-dialog.component";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { ContentService } from "../../../../services/content/content.service";
import { TokenEnrollmentDialogData, TokenService } from "../../../../services/token/token.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockMatDialogRef } from "../../../../../testing/mock-mat-dialog-ref";
import { MockContentService, MockTokenService } from "../../../../../testing/mock-services";

describe("TokenEnrollmentLastStepDialogComponent", () => {
  let component: TokenEnrollmentLastStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentLastStepDialogComponent>;
  const mockDialogData: TokenEnrollmentDialogData = {
    response: {
      type: "totp",
      detail: {
        type: "totp",
        serial: "1234567890",
        googleurl: {
          description: "Google Authenticator URL",
          img: "",
          value: "otpauth://totp/Example:user?secret=ABCDEF1234567890&issuer=Example"
        }
      },
      result: { status: true }
    },
    tokenType: "totp",
    userRealm: "test-realm",
    onlyAddToRealm: false,
    enrollParameters: { data: {} as any, mapper: jest.fn() as any }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, TokenEnrollmentLastStepDialogComponent],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: ContentService, useClass: MockContentService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render title for normal enrollment", () => {
    expect(component["rollover"]).toBe(false);
    expect(component.title()).toBe("Token Successfully Enrolled");
  });

  it("should render title for rollover", () => {
    mockDialogData.rollover = true;
    fixture = TestBed.createComponent(TokenEnrollmentLastStepDialogComponent);
    component = fixture.componentInstance;

    expect(component["rollover"]).toBe(true);
    expect(component.title()).toBe("Token Successfully Rolled Over");
  });
});
