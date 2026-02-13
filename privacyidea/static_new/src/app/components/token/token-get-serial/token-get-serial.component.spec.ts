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

import { provideHttpClient, HttpParams } from "@angular/common/http";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { Router } from "@angular/router";
import { Subject, of, Subscription } from "rxjs";
import { MockMatDialogRef } from "../../../../testing/mock-mat-dialog-ref";
import {
  MockTokenService,
  MockNotificationService,
  MockDialogService,
  MockContentService
} from "../../../../testing/mock-services";
import { ContentService } from "../../../services/content/content.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { TokenService } from "../../../services/token/token.service";
import {
  GetSerialResultDialogComponent,
  GetSerialResultDialogReturn
} from "./get-serial-result-dialog/get-serial-result-dialog.component";
import { TokenGetSerialComponent } from "./token-get-serial.component";
import { SearchTokenDialogComponent } from "./search-token-dialog/search-token-dialog";
import { DialogService } from "../../../services/dialog/dialog.service";

const makeCountResp = (count: number) => ({ result: { value: { count } } }) as any;

const makeSerialResp = (serial?: string) => ({ result: { value: { serial } } }) as any;

let confirmClosed$: Subject<boolean | GetSerialResultDialogReturn>;
let lastResultDialogData: any;

const routerMock = {
  navigateByUrl: jest.fn().mockResolvedValue(true)
} as unknown as jest.Mocked<Router>;

describe("TokenGetSerialComponent", () => {
  let fixture: ComponentFixture<TokenGetSerialComponent>;
  let component: TokenGetSerialComponent;
  let tokenServiceMock: MockTokenService;
  let notificationServiceMock: MockNotificationService;
  let dialogServiceMock: MockDialogService;

  beforeEach(async () => {
    jest.clearAllMocks();

    lastResultDialogData = undefined;

    await TestBed.configureTestingModule({
      imports: [TokenGetSerialComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: NotificationService, useClass: MockNotificationService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: Router, useValue: routerMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokenGetSerialComponent);
    component = fixture.componentInstance;

    tokenServiceMock = TestBed.inject(TokenService) as unknown as MockTokenService;
    notificationServiceMock = TestBed.inject(NotificationService) as unknown as MockNotificationService;
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;

    (tokenServiceMock as any).getSerial = jest.fn();
    confirmClosed$ = new Subject<boolean | GetSerialResultDialogReturn>();
    let dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed$);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    fixture.detectChanges();
  });

  it("creates", () => {
    expect(component).toBeTruthy();
  });

  it("getParams builds query from signals", () => {
    component.countWindow.set(25);
    component.assignmentState.set("assigned");
    component.tokenType.set("totp");
    component.serialSubstring.set("ABC");

    const p = component.getParams();
    expect(p.get("window")).toBe("25");
    expect(p.get("assigned")).toBe("1");
    expect(p.get("unassigned")).toBeNull();
    expect(p.get("type")).toBe("totp");
    expect(p.get("serial")).toBe("ABC");

    component.assignmentState.set("unassigned");
    const p2 = component.getParams();
    expect(p2.get("unassigned")).toBe("1");
    expect(p2.get("assigned")).toBeNull();
  });

  it("countTokens: guards invalid states", () => {
    component.currentStep.set("searching");
    component.countTokens();
    expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Invalid action.");
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

    component.otpValue.set("000000");
    component.countWindow.set(10);
    component.tokenType.set("hotp");
    component.serialSubstring.set("SER");

    component.countTokens();

    expect(tokenServiceMock.getSerial).toHaveBeenCalledTimes(2);
    expect(component.currentStep()).toBe("found");
    expect(component.foundSerial()).toBe("SER-1");
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: GetSerialResultDialogComponent,
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
    component.otpValue.set("000000");
    component.countTokens();
    TestBed.flushEffects();
    expect(component.currentStep()).toBe("countDone");
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({ component: SearchTokenDialogComponent, data: "150" });
    confirmClosed$.next(true);
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: GetSerialResultDialogComponent,
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

  it("findSerial: guards invalid state", () => {
    component.currentStep.set("init");
    component.findSerial();
    expect(notificationServiceMock.openSnackBar).toHaveBeenCalledWith("Invalid action.");
    expect(tokenServiceMock.getSerial as jest.Mock).not.toHaveBeenCalled();
  });

  it("findSerial: opens dialog ", () => {
    component.currentStep.set("countDone");
    (tokenServiceMock.getSerial as jest.Mock).mockReturnValue(of(makeSerialResp("J-007")));
    component.findSerial();
    expect(dialogServiceMock.openDialog).toHaveBeenCalledWith({
      component: GetSerialResultDialogComponent,
      data: { foundSerial: "J-007", otpValue: "" }
    });
    expect(component.foundSerial()).toBe("J-007");
    expect(component.currentStep()).toBe("found");
    lastResultDialogData = dialogServiceMock.openDialog.mock.calls.slice(-1)[0]?.[0]?.data;

    expect(lastResultDialogData).toBeDefined();
  });

  it("onClickRunSearch toggles count ↔ reset depending on step", () => {
    (tokenServiceMock.getSerial as jest.Mock)
      .mockImplementationOnce(() => of(makeCountResp(1)))
      .mockImplementationOnce(() => of(makeSerialResp("A-1")));

    component.currentStep.set("init");
    component.onClickRunSearch();
    expect(component.currentStep()).toBe("found");

    component.currentStep.set("counting");
    const resetSpy = jest.spyOn(component as any, "resetSteps");
    component.onClickRunSearch();
    expect(resetSpy).toHaveBeenCalled();
  });

  it("resetSteps unsubscribes serialSubscription and clears state", () => {
    const src$ = new Subject<any>();
    const sub: Subscription = src$.subscribe();
    (component as any).serialSubscription = sub;

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
