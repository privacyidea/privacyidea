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
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { ContentService } from "@services/content/content.service";
import { MockContentService } from "@testing/mock-services/mock-content-service";
import {
  ContainerTokensEnrolledDialogComponent,
  ContainerTokensEnrolledDialogData,
  EnrolledTokenInfo
} from "./container-tokens-enrolled-dialog.component";
import { BaseApiPayloadMapper, EnrollmentResponse } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { By } from "@angular/platform-browser";
import { TokenEnrollmentDataComponent } from "@components/token/token-enrollment/token-enrollment-data/token-enrollment-data.component";
import { TokenService, TokenTypeKey } from "@services/token/token.service";
import { of } from "rxjs";
import { MockTokenService } from "@testing/mock-services";

const dialogClose = jest.fn();
const dialogRefMock = { close: dialogClose };

const makeToken = (serial: string, type: TokenTypeKey): EnrolledTokenInfo => ({
  serial,
  type,
  googleurl: { img: "img", value: "url", description: "" },
  enrollmentParameters: {
    data: { type, serial, generateOnServer: true },
    mapper: new BaseApiPayloadMapper()
  }
});

const threeTokens: ContainerTokensEnrolledDialogData = {
  containerSerial: "CONT-001",
  enrolledTokens: [makeToken("TOK-1", "hotp"), makeToken("TOK-2", "totp"), makeToken("TOK-3", "daypassword")]
};

describe("ContainerTokensEnrolledDialogComponent", () => {
  let component: ContainerTokensEnrolledDialogComponent;
  let fixture: ComponentFixture<ContainerTokensEnrolledDialogComponent>;
  let contentService: MockContentService;

  beforeEach(async () => {
    jest.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [ContainerTokensEnrolledDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: threeTokens },
        { provide: ContentService, useClass: MockContentService },
        { provide: TokenService, useClass: MockTokenService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTokensEnrolledDialogComponent);
    component = fixture.componentInstance;
    contentService = TestBed.inject(ContentService) as unknown as MockContentService;
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  describe("regenerating one of the tokens", () => {
    const regenerated = (detail: Record<string, unknown>): EnrollmentResponse =>
      ({
        type: "hotp",
        result: { status: true },
        detail: { type: "hotp", ...detail }
      }) as unknown as EnrollmentResponse;

    const emitRegenerated = (response: EnrollmentResponse) => {
      fixture.debugElement
        .query(By.css("app-token-enrollment-data"))
        .triggerEventHandler("enrollmentResponseChange", response);
      fixture.detectChanges();
    };

    it("passes the enrollment parameters of the current token to the enrollment data", () => {
      const enrollmentData = fixture.debugElement.query(By.directive(TokenEnrollmentDataComponent))
        .componentInstance as TokenEnrollmentDataComponent;

      expect(enrollmentData.enrollmentParameters()).toBe(threeTokens.enrolledTokens[0].enrollmentParameters);
      expect(enrollmentData.enrolledInputData()).toBe(threeTokens.enrolledTokens[0]);
    });

    it("regenerating via the button keeps the new QR code while paging through the tokens", () => {
      const tokenService = TestBed.inject(TokenService) as unknown as MockTokenService;
      tokenService.enrollToken = jest
        .fn()
        .mockReturnValue(
          of(regenerated({ serial: "TOK-1", googleurl: { img: "regenerated-img", value: "regenerated-url" } }))
        );
      const regenerateButton = Array.from(fixture.nativeElement.querySelectorAll("button")).find((button) =>
        (button as HTMLButtonElement).textContent?.includes("Regenerate QR Code")
      ) as HTMLButtonElement;
      expect(regenerateButton).toBeTruthy();

      regenerateButton.click();
      fixture.detectChanges();

      expect(tokenService.enrollToken).toHaveBeenCalledWith(
        expect.objectContaining({ data: expect.objectContaining({ serial: "TOK-1", generateOnServer: true }) })
      );
      expect(component.currentToken().googleurl?.img).toBe("regenerated-img");

      component.next();
      component.previous();
      fixture.detectChanges();

      expect(component.currentToken().googleurl?.img).toBe("regenerated-img");
      const enrollmentData = fixture.debugElement.query(By.directive(TokenEnrollmentDataComponent))
        .componentInstance as TokenEnrollmentDataComponent;
      expect(enrollmentData.enrolledData().googleurl?.img).toBe("regenerated-img");
    });

    it("shows the regenerated data and leaves the other tokens untouched", () => {
      emitRegenerated(
        regenerated({ serial: "TOK-1", googleurl: { img: "regenerated-img", value: "regenerated-url" } })
      );

      expect(component.currentToken().googleurl?.img).toBe("regenerated-img");
      expect(component.enrolledTokens()[1].googleurl?.img).toBe("img");
      expect(component.total()).toBe(3);
    });

    it("keeps the regenerated data when paging away and back", () => {
      emitRegenerated(
        regenerated({ serial: "TOK-1", googleurl: { img: "regenerated-img", value: "regenerated-url" } })
      );

      component.next();
      component.previous();

      expect(component.currentToken().googleurl?.img).toBe("regenerated-img");
    });

    it("keeps regenerated OTP values of a value based token when paging away and back", () => {
      emitRegenerated(regenerated({ serial: "TOK-1", otps: { "0": "111111", "1": "222222" } }));

      component.next();
      component.previous();

      expect(component.currentToken()["otps"]).toEqual({ "0": "111111", "1": "222222" });
    });

    it("keeps serial, type and enrollment parameters of the regenerated token", () => {
      emitRegenerated(
        regenerated({ serial: "TOK-1", googleurl: { img: "regenerated-img", value: "regenerated-url" } })
      );

      expect(component.currentToken().serial).toBe("TOK-1");
      expect(component.currentToken().type).toBe("hotp");
      expect(component.currentToken().enrollmentParameters).toBe(threeTokens.enrolledTokens[0].enrollmentParameters);
    });

    it("regenerating the second token does not affect the first one", () => {
      component.next();
      fixture.detectChanges();

      emitRegenerated(
        regenerated({ serial: "TOK-2", googleurl: { img: "regenerated-img", value: "regenerated-url" } })
      );

      expect(component.currentToken().serial).toBe("TOK-2");
      expect(component.currentToken().googleurl?.img).toBe("regenerated-img");

      component.previous();
      expect(component.currentToken().googleurl?.img).toBe("img");
    });
  });

  it("starts on first token with correct total and progress", () => {
    expect(component.currentIndex()).toBe(0);
    expect(component.total()).toBe(3);
    expect(component.isFirst()).toBe(true);
    expect(component.isLast()).toBe(false);
    expect(component.progress()).toBeCloseTo(33.3, 0);
  });

  it("next() advances to second token", () => {
    component.next();
    expect(component.currentIndex()).toBe(1);
    expect(component.isFirst()).toBe(false);
    expect(component.isLast()).toBe(false);
  });

  it("previous() goes back from second to first token", () => {
    component.next();
    component.previous();
    expect(component.currentIndex()).toBe(0);
    expect(component.isFirst()).toBe(true);
  });

  it("next() does not advance past last token", () => {
    component.next();
    component.next();
    component.next();
    expect(component.currentIndex()).toBe(2);
    expect(component.isLast()).toBe(true);
  });

  it("previous() does not go before first token", () => {
    component.previous();
    expect(component.currentIndex()).toBe(0);
  });

  it("isLast() is true on last token and progress is 100%", () => {
    component.next();
    component.next();
    expect(component.isLast()).toBe(true);
    expect(component.progress()).toBe(100);
  });

  it("dialogActions: Previous button is disabled on first token", () => {
    const prev = component.dialogActions().find((a) => a.value === "previous")!;
    expect(prev.disabled).toBe(true);
  });

  it("dialogActions: Previous button is enabled after first token", () => {
    component.next();
    const prev = component.dialogActions().find((a) => a.value === "previous")!;
    expect(prev.disabled).toBe(false);
  });

  it("dialogActions: shows Next action when not on last token", () => {
    const hasNext = component.dialogActions().some((a) => a.value === "next");
    const hasFinish = component.dialogActions().some((a) => a.value === "finish");
    expect(hasNext).toBe(true);
    expect(hasFinish).toBe(false);
  });

  it("dialogActions: shows Finish action on last token", () => {
    component.next();
    component.next();
    const hasNext = component.dialogActions().some((a) => a.value === "next");
    const hasFinish = component.dialogActions().some((a) => a.value === "finish");
    expect(hasNext).toBe(false);
    expect(hasFinish).toBe(true);
  });

  it("onDialogAction('next') advances index", () => {
    component.onDialogAction("next");
    expect(component.currentIndex()).toBe(1);
  });

  it("onDialogAction('previous') decrements index", () => {
    component.next();
    component.onDialogAction("previous");
    expect(component.currentIndex()).toBe(0);
  });

  it("onDialogAction('finish') closes dialog and navigates to container details", () => {
    component.onDialogAction("finish");
    expect(dialogClose).toHaveBeenCalled();
    expect(contentService.navigateContainerDetails).toHaveBeenCalledWith("CONT-001");
  });

  it("finish() closes dialog and navigates to container details", () => {
    component.finish();
    expect(dialogClose).toHaveBeenCalled();
    expect(contentService.navigateContainerDetails).toHaveBeenCalledWith("CONT-001");
  });
});
