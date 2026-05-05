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
import { NewSmsGatewayComponent } from "./new-sms-gateway.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { of } from "rxjs";
import { SmsGatewayService } from "../../../../services/sms-gateway/sms-gateway.service";
import { MockSmsGatewayService } from "../../../../../testing/mock-services/mock-sms-gateway-service";
import { SaveAndExitDialogComponent } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { PendingChangesService } from "../../../../services/pending-changes/pending-changes.service";
import { MockPendingChangesService } from "../../../../../testing/mock-services/mock-pending-changes-service";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { MockDialogService } from "../../../../../testing/mock-services";
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from "@angular/router";
import { ROUTE_PATHS } from "../../../../route_paths";

describe("NewSmsGatewayComponent", () => {
  let component: NewSmsGatewayComponent;
  let fixture: ComponentFixture<NewSmsGatewayComponent>;
  let smsGatewayServiceMock: any;
  let router: Router;
  let pendingChangesService: MockPendingChangesService;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewSmsGatewayComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({})) }
        },
        { provide: SmsGatewayService, useClass: MockSmsGatewayService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    smsGatewayServiceMock = TestBed.inject(SmsGatewayService);
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);

    (smsGatewayServiceMock.smsProvidersResource as any).value.set({
      result: {
        value: {
          mod1: { parameters: { p1: { description: "desc1" } } }
        }
      }
    });

    fixture = TestBed.createComponent(NewSmsGatewayComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode).toBe(false);
    expect(component.smsForm.get("name")?.value).toBe("");
  });

  it("should update form when provider changes", async () => {
    component.smsForm.get("providermodule")?.setValue("mod1");
    fixture.detectChanges();
    await fixture.whenStable();
    expect(component.parametersForm.get("p1")).toBeDefined();
  });

  it("should call save when form is valid", async () => {
    component.smsForm.patchValue({
      name: "test",
      providermodule: "mod1"
    });

    const success = await component.save();

    expect(success).toBe(true);
    expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
  });

  it("Save should handle error", async () => {
    component.smsForm.patchValue({
      name: "test",
      providermodule: "mod1"
    });
    smsGatewayServiceMock.postSmsGateway = jest.fn().mockRejectedValue(new Error("Save failed"));

    const success = await component.save();

    expect(success).toBe(false);
    expect(smsGatewayServiceMock.postSmsGateway).toHaveBeenCalled();
    expect(router.navigateByUrl).not.toHaveBeenCalled();
  });

  describe("onCancel", () => {
    let mockSaveExitDialogRef: any;

    beforeEach(() => {
      mockSaveExitDialogRef = {
        afterClosed: jest.fn()
      };
      dialogService.openDialog.mockReturnValue(mockSaveExitDialogRef);
    });

    it("should navigate back directly when there are no changes", () => {
      component.onCancel();

      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should open SaveAndExitDialog when there are changes", () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.smsForm.patchValue({
        name: "test",
        providermodule: "mod1"
      });
      component.smsForm.markAsDirty();

      component.onCancel();

      expect(dialogService.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({
          component: SaveAndExitDialogComponent,
          data: expect.objectContaining({
            allowSaveExit: true
          })
        })
      );
    });

    it("should navigate back when user selects 'discard' in cancel dialog", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.smsForm.patchValue({
        name: "test",
        providermodule: "mod1"
      });
      component.smsForm.markAsDirty();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should navigate back when user selects 'save-exit' and save succeeds", async () => {
      component.smsForm.patchValue({
        name: "test",
        providermodule: "mod1"
      });
      component.smsForm.markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(true));

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).toHaveBeenCalled();
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_SMS);
    });

    it("should NOT navigate back when user selects 'save-exit' but save fails", async () => {
      component.smsForm.patchValue({
        name: "test",
        providermodule: "mod1"
      });
      component.smsForm.markAsDirty();
      smsGatewayServiceMock.postSmsGateway = jest.fn().mockRejectedValue(new Error("Save failed"));
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      pendingChangesService.save.mockReturnValue(Promise.resolve(false));

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user selects 'save-exit' but canSave is false", async () => {
      component.smsForm.patchValue({ name: "" });
      component.smsForm.markAsDirty();
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of("save-exit"));

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(pendingChangesService.save).not.toHaveBeenCalled();
      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });

    it("should do nothing when user closes dialog without selecting an option", async () => {
      mockSaveExitDialogRef.afterClosed.mockReturnValue(of(undefined));
      component.smsForm.patchValue({
        name: "test",
        providermodule: "mod1"
      });
      component.smsForm.markAsDirty();

      component.onCancel();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(pendingChangesService.clearAllRegistrations).not.toHaveBeenCalled();
      expect(router.navigateByUrl).not.toHaveBeenCalled();
    });
  });
});
