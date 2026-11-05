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

import { HttpParams, provideHttpClient } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import {
  FindSerialResultDialogComponent,
  GetSerialResultDialogData,
  GetSerialResultDialogReturn
} from "@components/token/token-find-serial/find-serial-result-dialog/find-serial-result-dialog.component";
import { ContentService } from "@services/content/content.service";
import { DialogService } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { TokenService } from "@services/token/token.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import {
  MockContentService,
  MockDialogService,
  MockNotificationService,
  MockPiResponse,
  MockRouter,
  MockTokenService
} from "@testing/mock-services";
import { of, Subject, Subscription } from "rxjs";
import { SearchTokenDialogComponent } from "./search-token-dialog/search-token-dialog";
import { TokenFindSerialComponent } from "./token-find-serial.component";

interface SerialPayload {
  count: number;
  serial?: string;
}

const makeCountResp = (count: number) => MockPiResponse.fromValue<SerialPayload>({ count });

const makeSerialResp = (serial?: string) => MockPiResponse.fromValue<SerialPayload>({ count: 0, serial });

let confirmClosed$: Subject<boolean | GetSerialResultDialogReturn>;
let lastResultDialogData: GetSerialResultDialogData | undefined;

describe("TokenGetSerialComponent", () => {
  let fixture: ComponentFixture<TokenFindSerialComponent>;
  let component: TokenFindSerialComponent;
  let tokenServiceMock: MockTokenService;
  let notificationServiceMock: MockNotificationService;
  let dialogServiceMock: MockDialogService;

  beforeEach(async () => {
    jest.clearAllMocks();

    lastResultDialogData = undefined;

    await TestBed.configureTestingModule({
      imports: [TokenFindSerialComponent],
      providers: [
        provideHttpClient(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: Router, useClass: MockRouter }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenFindSerialComponent);
    component = fixture.componentInstance;

    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;

    tokenServiceMock.getSerial = jest.fn();
    confirmClosed$ = new Subject<boolean | GetSerialResultDialogReturn>();
    const dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed$);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  const patchModel = (patch: Partial<ReturnType<typeof component.searchModel>>) =>
    component.searchModel.update((model) => ({ ...model, ...patch }));
  const input = (id: string): HTMLInputElement => fixture.nativeElement.querySelector(`#${id}`);
  const typeInto = (el: HTMLInputElement, value: string) => {
    el.value = value;
    el.dispatchEvent(new Event("input"));
    fixture.detectChanges();
  };
  const runButton = (): HTMLButtonElement => fixture.nativeElement.querySelector(".action-button-primary");

  it("getParams builds query from the model", () => {
    patchModel({ countWindow: 25, assignmentState: "assigned", tokenType: "totp", serialSubstring: "ABC" });

    const p = component.getParams();
    expect(p.get("window")).toBe("25");
    expect(p.get("assigned")).toBe("1");
    expect(p.get("unassigned")).toBeNull();
    expect(p.get("type")).toBe("totp");
    expect(p.get("serial")).toBe("ABC");

    patchModel({ assignmentState: "unassigned" });
    const p2 = component.getParams();
    expect(p2.get("unassigned")).toBe("1");
    expect(p2.get("assigned")).toBeNull();
  });

  it("countTokens: guards invalid states", () => {
    component.currentStep.set("searching");
    component.countTokens();
    expect(notificationServiceMock.warning).toHaveBeenCalledWith("Invalid action.");
    expect(tokenServiceMock.getSerial as jest.Mock).not.toHaveBeenCalled();
  });

  it("small count: counts then immediately finds and opens result dialog", () => {
    (tokenServiceMock.getSerial as jest.Mock)
      .mockImplementationOnce((_otp: string, params: HttpParams) => {
        expect(params.get("count")).toBe("1");
        return of(makeCountResp(3));
      })
      .mockImplementationOnce((_otp: string, params: HttpParams) => {
        expect(params.get("count")).toBeNull();
        return of(makeSerialResp("SER-1"));
      });

    patchModel({ otpValue: "000000", countWindow: 10, tokenType: "hotp", serialSubstring: "SER" });

    component.countTokens();

    expect(tokenServiceMock.getSerial).toHaveBeenCalledTimes(2);
    expect(component.currentStep()).toBe("found");
    expect(component.foundSerial()).toBe("SER-1");
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: FindSerialResultDialogComponent,
      data: {
        foundSerial: "SER-1",
        otpValue: "000000"
      }
    });
  });

  it("large count: asks confirmation, proceed -> find; cancel -> reset", async () => {
    (tokenServiceMock.getSerial as jest.Mock)
      .mockImplementationOnce((_otp: string, params: HttpParams) => {
        expect(params.get("count")).toBe("1");
        return of(makeCountResp(150));
      })
      .mockImplementationOnce(() => of(makeSerialResp("BIG-1")));
    patchModel({ otpValue: "000000" });
    TestBed.tick();
    component.countTokens();

    expect(component.currentStep()).toBe("countDone");
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({ component: SearchTokenDialogComponent, data: "150" });
    confirmClosed$.next(true);
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: FindSerialResultDialogComponent,
      data: {
        foundSerial: "BIG-1",
        otpValue: "000000"
      }
    });
    expect(tokenServiceMock.getSerial).toHaveBeenCalledTimes(2);
    expect(component.currentStep()).toBe("found");
    expect(component.foundSerial()).toBe("BIG-1");

    (tokenServiceMock.getSerial as jest.Mock).mockReset().mockImplementationOnce(() => of(makeCountResp(100)));

    component.resetSteps();
    expect(component.currentStep()).toBe("init");
    component.countTokens();
    expect(component.currentStep()).toBe("countDone");

    confirmClosed$.next(false);
    confirmClosed$.next("reset");
    confirmClosed$.complete();

    expect(tokenServiceMock.getSerial as jest.Mock).toHaveBeenCalledTimes(1);
    expect(component.currentStep()).toBe("init");
  });

  it("getParams omits the window when the count window is empty", () => {
    patchModel({ countWindow: null });
    expect(component.getParams().has("window")).toBe(false);
  });

  it("starts with the search button disabled and enables it once an OTP value is typed", () => {
    expect(runButton().disabled).toBe(true);
    typeInto(input("otpValue"), "123456");
    expect(component.searchModel().otpValue).toBe("123456");
    expect(runButton().disabled).toBe(false);
  });

  it("rejects a whitespace-only OTP value", () => {
    typeInto(input("otpValue"), "   ");
    expect(
      component.searchForm
        .otpValue()
        .errors()
        .map((e) => e.kind)
    ).toEqual(["required"]);
    expect(runButton().disabled).toBe(true);
  });

  it("countTokens does not search while the form is invalid and touches the fields", () => {
    component.countTokens();
    fixture.detectChanges();
    expect(tokenServiceMock.getSerial as jest.Mock).not.toHaveBeenCalled();
    expect(component.currentStep()).toBe("init");
    expect(component.searchForm.otpValue().touched()).toBe(true);
    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("OTP value is required");
  });

  it("an empty count window is required and disables the search button", () => {
    patchModel({ otpValue: "000000" });
    typeInto(input("countWindow"), "");
    expect(component.searchModel().countWindow).toBeNull();
    expect(
      component.searchForm
        .countWindow()
        .errors()
        .map((e) => e.kind)
    ).toEqual(["required"]);
    expect(runButton().disabled).toBe(true);
  });

  it("a count window below 1 fails the min rule and renders its message once touched", () => {
    patchModel({ otpValue: "000000" });
    typeInto(input("countWindow"), "0");
    input("countWindow").dispatchEvent(new Event("blur"));
    fixture.detectChanges();
    expect(
      component.searchForm
        .countWindow()
        .errors()
        .map((e) => e.kind)
    ).toEqual(["min"]);
    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("at least 1");
  });

  it("a bad number input reports parse and renders the number message", () => {
    patchModel({ otpValue: "000000" });
    const el = input("countWindow");
    Object.defineProperty(el, "validity", { value: { badInput: true }, configurable: true });
    typeInto(el, "");
    el.dispatchEvent(new Event("blur"));
    fixture.detectChanges();
    expect(
      component.searchForm
        .countWindow()
        .errors()
        .map((e) => e.kind)
    ).toContain("parse");
    expect(fixture.nativeElement.querySelector("mat-error")?.textContent).toContain("Enter a valid number.");
  });

  it("disables the OTP value once a search has left the init step", () => {
    expect(component.searchForm.otpValue().disabled()).toBe(false);
    component.currentStep.set("counting");
    expect(component.searchForm.otpValue().disabled()).toBe(true);
  });

  it("keeps the button enabled as Stop while a search is running", () => {
    patchModel({ otpValue: "000000", countWindow: null });
    TestBed.tick();
    component.currentStep.set("searching");
    fixture.detectChanges();
    expect(component.runSearchDisabled()).toBe(false);
    expect(runButton().disabled).toBe(false);
  });

  it("a changed search option resets the steps", () => {
    component.currentStep.set("found");
    TestBed.tick();
    patchModel({ tokenType: "totp" });
    TestBed.tick();
    expect(component.currentStep()).toBe("init");
  });

  it("changing the count window does not reset the steps", () => {
    TestBed.tick();
    component.currentStep.set("found");
    patchModel({ countWindow: 5 });
    TestBed.tick();
    expect(component.currentStep()).toBe("found");
  });

  it("picking an assignment state in the select updates the model and resets the steps", () => {
    TestBed.tick();
    component.currentStep.set("found");
    const selects = fixture.nativeElement.querySelectorAll("mat-select .mat-mdc-select-trigger");
    (selects[1] as HTMLElement).click();
    fixture.detectChanges();
    const options = Array.from(document.querySelectorAll("mat-option")) as HTMLElement[];
    options.find((o) => o.textContent?.includes("is assigned to a user"))?.click();
    fixture.detectChanges();
    TestBed.tick();
    expect(component.searchModel().assignmentState).toBe("assigned");
    expect(component.currentStep()).toBe("init");
  });

  it("findSerial: guards invalid state", () => {
    component.currentStep.set("init");
    component.findSerial();
    expect(notificationServiceMock.warning).toHaveBeenCalledWith("Invalid action.");
    expect(tokenServiceMock.getSerial as jest.Mock).not.toHaveBeenCalled();
  });

  it("findSerial: opens dialog ", () => {
    component.currentStep.set("countDone");
    (tokenServiceMock.getSerial as jest.Mock).mockReturnValue(of(makeSerialResp("J-007")));
    component.findSerial();
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: FindSerialResultDialogComponent,
      data: { foundSerial: "J-007", otpValue: "" }
    });
    expect(component.foundSerial()).toBe("J-007");
    expect(component.currentStep()).toBe("found");
    lastResultDialogData = dialogServiceMock.openDialog.mock.calls.slice(-1)[0]?.[0]?.data as GetSerialResultDialogData;

    expect(lastResultDialogData).toBeDefined();
  });

  it("onClickRunSearch toggles count ↔ reset depending on step", () => {
    (tokenServiceMock.getSerial as jest.Mock)
      .mockImplementationOnce(() => of(makeCountResp(1)))
      .mockImplementationOnce(() => of(makeSerialResp("A-1")));

    patchModel({ otpValue: "000000" });
    TestBed.tick();
    component.currentStep.set("init");
    component.onClickRunSearch();
    expect(component.currentStep()).toBe("found");

    component.currentStep.set("counting");
    const resetSpy = jest.spyOn(component, "resetSteps");
    component.onClickRunSearch();
    expect(resetSpy).toHaveBeenCalled();
  });

  it("resetSteps unsubscribes serialSubscription and clears state", () => {
    const src$ = new Subject<void>();
    const sub: Subscription = src$.subscribe();
    component.serialSubscription = sub;

    expect(sub.closed).toBe(false);
    component.resetSteps();
    expect(sub.closed).toBe(true);
    expect(component.currentStep()).toBe("init");
    expect(component.foundSerial()).toBe("");
    expect(component.tokenCount()).toBe("");
  });

  it("countIsLarge returns true for >= 100", () => {
    component.tokenCount.set("99");
    expect(component.countIsLarge()).toBe(false);
    component.tokenCount.set("100");
    expect(component.countIsLarge()).toBe(true);
    component.tokenCount.set("150");
    expect(component.countIsLarge()).toBe(true);
  });
});
