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
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatAutocompleteModule } from "@angular/material/autocomplete";
import { ReactiveFormsModule } from "@angular/forms";
import { TokenEnrollmentFirstStepDialogComponent } from "./token-enrollment-first-step-dialog.component";
import { provideHttpClient } from "@angular/common/http";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import "@angular/localize/init";

describe("TokenEnrollmentFirstStepDialogComponent", () => {
  let component: TokenEnrollmentFirstStepDialogComponent;
  let fixture: ComponentFixture<TokenEnrollmentFirstStepDialogComponent>;
  const dialogRefMock = {
    close: jest.fn()
  } as unknown as jest.Mocked<
    MatDialogRef<TokenEnrollmentFirstStepDialogComponent, string | null>
  >;

  const dialogDataStub = {
    enrollmentResponse: {
      detail: {
        rollout_state: "enrolled",
        serial: "1234567890",
        threadid: 1,
        passkey_registration: null,
        u2fRegisterRequest: null,
        pushurl: {
          description: "Push URL",
          img: "push.png",
          value: "https://example.com/push",
          value_b32: "B32VALUE"
        },
        googleurl: {
          description: "Google URL",
          img: "google.png",
          value: "https://example.com/google",
          value_b32: "B32VALUE"
        },
        otpkey: {
          description: "OTP Key",
          img: "otp.png",
          value: "otpprotocol://example.com/otpkey",
          value_b32: "B32VALUE"
        },
        motpurl: {
          description: "MOTP URL",
          img: "motp.png",
          value: "motpprotocol://example.com/motpkey",
          value_b32: "B32VALUE"
        },
        tiqrenroll: {
          description: "Tiqr Enroll URL",
          img: "tiqr.png",
          value: "tiqr://example.com/enroll",
          value_b32: "B32VALUE"
        }
      }
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: dialogDataStub }
      ],
      imports: [
        MatFormFieldModule,
        MatAutocompleteModule,
        ReactiveFormsModule,
        TokenEnrollmentFirstStepDialogComponent
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenEnrollmentFirstStepDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
