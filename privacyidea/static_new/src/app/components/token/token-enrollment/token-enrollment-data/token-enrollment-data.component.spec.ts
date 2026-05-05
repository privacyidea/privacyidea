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
import { NO_ERRORS_SCHEMA } from "@angular/core";

import { TokenEnrollmentDataComponent } from "./token-enrollment-data.component";
import { MockContentService } from "src/testing/mock-services/mock-content-service";
import { TokenService } from "../../../../services/token/token.service";
import { ContentService } from "../../../../services/content/content.service";
import { MockTokenService } from "../../../../../testing/mock-services";
import { of } from "rxjs";
import { MockNotificationService } from "src/testing/mock-services/mock-notification-service";
import { NotificationService } from "../../../../services/notification/notification.service";

describe("TokenEnrollmentDataComponent", () => {
  let component: TokenEnrollmentDataComponent;
  let fixture: ComponentFixture<TokenEnrollmentDataComponent>;
  let mockTokenService: MockTokenService;
  let mockNotificationService: MockNotificationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrollmentDataComponent],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: ContentService, useClass: MockContentService },
        { provide: NotificationService, useClass: MockNotificationService }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenEnrollmentDataComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    mockTokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
    mockNotificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render inputs if provided", () => {
    fixture.componentRef.setInput("enrolledInputData", {
      serial: "SERIAL123",
      container_serial: "CONT123",
      googleurl: { img: "img", value: "123" }
    });
    fixture.detectChanges();
    expect(component["serial"]()).toBe("SERIAL123");
    expect(component["containerSerial"]()).toBe("CONT123");
    expect(component.enrolledData()).toEqual({
      serial: "SERIAL123",
      container_serial: "CONT123",
      googleurl: { img: "img", value: "123" }
    });
    expect(component["qrCode"]()).toEqual(("img"));
    expect(component["url"]()).toEqual("123");
  });

  it("should show QR code if tokenType allows", () => {
    fixture.componentRef.setInput("tokenType", "hotp");
    fixture.detectChanges();
    expect(component.showQRCode()).toBe(true);
    expect(component.showRegenerateButton()).toBe(true);
  });

  it("should not show QR code for types in NO_QR_CODE_TOKEN_TYPES", () => {
    fixture.componentRef.setInput("tokenType", "email");
    fixture.detectChanges();
    expect(component.showQRCode()).toBe(false);
  });

  it("should show regenerate button if tokenType allows", () => {
    fixture.componentRef.setInput("tokenType", "hotp");
    fixture.detectChanges();
    expect(component.showRegenerateButton()).toBe(true);
  });

  it("should not show regenerate button if tokenType not allows", () => {
    fixture.componentRef.setInput("tokenType", "spass");
    fixture.detectChanges();
    expect(component.showRegenerateButton()).toBe(false);
  });

  it("should adopt regenerate button text to token type", () => {
    fixture.componentRef.setInput("tokenType", "spass");
    fixture.detectChanges();
    expect(component.regenerateButtonText()).toEqual("Regenerate QR Code");

    fixture.componentRef.setInput("tokenType", "tan");
    fixture.detectChanges();
    expect(component.regenerateButtonText()).toEqual("Regenerate Values");
  });

  it("should call enrollToken and update enrolledData on regenerateQRCode", () => {
    mockTokenService.enrollToken = jest.fn().mockReturnValue(of({
      detail: {
        serial: "SERIAL123",
        googleurl: { img: "new_img", value: "456" }
      }
    }));
    fixture.componentRef.setInput("enrollmentParameters", {
      data: { serial: "SERIAL123" },
      mapper: { map: jest.fn() }
    });
    fixture.componentRef.setInput("enrolledInputData", { serial: "SERIAL123", container_serial: "CONT123" });
    fixture.detectChanges();
    component.regenerateQRCode();
    expect(mockTokenService.enrollToken).toHaveBeenCalled();
    expect(component.enrolledData()).toEqual({ serial: "SERIAL123", googleurl: { img: "new_img", value: "456" } });
    expect(component["qrCode"]()).toEqual("new_img");
    expect(component["url"]()).toEqual("456");
  });

  it("should open notification if no enrollmentParameters are available on regenerateQRCode", () => {
    component.regenerateQRCode();
    expect(mockNotificationService.warning).toHaveBeenCalledWith("Enrollment parameters are missing. Cannot regenerate token.");
  });

  it("uses pushurl for QR code and URL when googleurl is absent (push token)", () => {
    fixture.componentRef.setInput("tokenType", "push");
    fixture.componentRef.setInput("enrolledInputData", {
      serial: "PUSH001",
      pushurl: { img: "push-qr-img", value: "push://enroll-url", description: "" }
    });
    fixture.detectChanges();
    expect(component["qrCode"]()).toBe("push-qr-img");
    expect(component["url"]()).toBe("push://enroll-url");
  });

  it("hasEnrollmentData is false for NO_QR_CODE type even when otpkey img is present (indexedsecret)", () => {
    fixture.componentRef.setInput("tokenType", "indexedsecret");
    fixture.componentRef.setInput("enrolledInputData", {
      serial: "IDX001",
      otpkey: { img: "some-qr-img", value: "hexkey", value_b32: "BASE32KEY", description: "" }
    });
    fixture.detectChanges();
    expect(component["hasEnrollmentData"]()).toBe(false);
  });

  it("hasEnrollmentData is false for spass (no QR, no otpkey, no otps)", () => {
    fixture.componentRef.setInput("tokenType", "spass");
    fixture.componentRef.setInput("enrolledInputData", { serial: "SPASS001" });
    fixture.detectChanges();
    expect(component["hasEnrollmentData"]()).toBe(false);
  });

  it("hasEnrollmentData is false for email token", () => {
    fixture.componentRef.setInput("tokenType", "email");
    fixture.componentRef.setInput("enrolledInputData", { serial: "EMAIL001" });
    fixture.detectChanges();
    expect(component["hasEnrollmentData"]()).toBe(false);
  });

  it("shows fallback serial message when no enrollment data is available", () => {
    fixture.componentRef.setInput("tokenType", "spass");
    fixture.componentRef.setInput("enrolledInputData", { serial: "SPASS001" });
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain("SPASS001");
    expect(text).toContain("successfully enrolled");
  });
});
