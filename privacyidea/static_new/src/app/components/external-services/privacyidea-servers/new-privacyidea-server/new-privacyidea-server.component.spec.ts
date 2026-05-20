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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogComponent } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { PrivacyideaServerService } from "@services/privacyidea-server/privacyidea-server.service";
import {
  MockAuthService,
  MockDialogService,
  MockPendingChangesService,
  MockPrivacyideaServerService
} from "@testing/mock-services";
import { BehaviorSubject, of } from "rxjs";
import { NewPrivacyideaServerComponent } from "./new-privacyidea-server.component";

describe("NewPrivacyideaServerComponent", () => {
  let component: NewPrivacyideaServerComponent;
  let fixture: ComponentFixture<NewPrivacyideaServerComponent>;
  let privacyideaServerServiceMock: any;
  let dialogServiceMock: MockDialogService;
  let router: Router;
  let paramMapSubject: BehaviorSubject<ParamMap>;

  beforeEach(async () => {
    paramMapSubject = new BehaviorSubject(convertToParamMap({}));

    await TestBed.configureTestingModule({
      imports: [NewPrivacyideaServerComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: PrivacyideaServerService, useClass: MockPrivacyideaServerService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: ActivatedRoute, useValue: { paramMap: paramMapSubject.asObservable() } }
      ]
    }).compileComponents();

    const authSvc = TestBed.inject(AuthService) as unknown as MockAuthService;
    authSvc.authData.set({ ...(authSvc.authData() as any), rights: ["privacyideaserver_write"] } as any);

    privacyideaServerServiceMock = TestBed.inject(PrivacyideaServerService);
    router = TestBed.inject(Router);

    fixture = TestBed.createComponent(NewPrivacyideaServerComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should initialize form for create mode", () => {
    expect(component.isEditMode()).toBe(false);
    expect(component.privacyideaModel().identifier).toBe("");
  });

  it("should initialize form for edit mode", () => {
    privacyideaServerServiceMock.remoteServerOptions = signal([{ identifier: "test", url: "http://test", tls: true }]);

    paramMapSubject.next(convertToParamMap({ identifier: "test" }));

    fixture.destroy();
    fixture = TestBed.createComponent(NewPrivacyideaServerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isEditMode()).toBe(true);
    expect(component.privacyideaModel().identifier).toBe("test");
    expect(component.privacyideaForm.identifier().disabled()).toBe(true);
  });

  it("should be invalid when required fields are missing", () => {
    component.privacyideaModel.update(m => ({ ...m, identifier: "", url: "" }));
    expect(component.privacyideaForm().valid()).toBe(false);
  });

  it("should call save when form is valid", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.privacyideaModel.update(m => ({ ...m, identifier: "test", url: "http://test" }));
    const success = await component.save();
    expect(success).toBe(true);
    expect(privacyideaServerServiceMock.postPrivacyideaServer).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
  });

  it("save should return false on error", async () => {
    component.privacyideaModel.update(m => ({ ...m, identifier: "test", url: "http://test" }));
    privacyideaServerServiceMock.postPrivacyideaServer = jest.fn().mockRejectedValue(new Error("post-failed"));

    const success = await component.save();
    expect(success).toBe(false);
    expect(privacyideaServerServiceMock.postPrivacyideaServer).toHaveBeenCalled();
  });

  it("should call test when form is valid", async () => {
    component.privacyideaModel.update(m => ({ ...m, identifier: "test", url: "http://test" }));
    component.test();
    expect(privacyideaServerServiceMock.testPrivacyideaServer).toHaveBeenCalled();
  });

  it("should navigate back on cancel without changes", () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.onCancel();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
  });

  it("should show confirmation dialog on cancel with changes", () => {
    component.privacyideaForm.description().markAsDirty();
    component.onCancel();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
  });

  it("save should return false when form is invalid", async () => {
    component.privacyideaModel.update((m) => ({ ...m, identifier: "", url: "" }));
    const result = await component.save();
    expect(result).toBe(false);
    expect(privacyideaServerServiceMock.postPrivacyideaServer).not.toHaveBeenCalled();
  });

  it("test should not call service when form is invalid", () => {
    component.privacyideaModel.update((m) => ({ ...m, identifier: "", url: "" }));
    component.test();
    expect(privacyideaServerServiceMock.testPrivacyideaServer).not.toHaveBeenCalled();
    expect(component.isTesting()).toBe(false);
  });

  it("test should set isTesting flag while waiting and reset on completion", async () => {
    component.privacyideaModel.update((m) => ({ ...m, identifier: "t", url: "http://t" }));
    let resolveFn: () => void;
    privacyideaServerServiceMock.testPrivacyideaServer = jest.fn(
      () => new Promise<void>((resolve) => (resolveFn = resolve))
    );
    component.test();
    expect(component.isTesting()).toBe(true);
    resolveFn!();
    await Promise.resolve();
    await Promise.resolve();
    expect(component.isTesting()).toBe(false);
  });

  describe("onCancel dialog handling", () => {
    let mockDialogRef: any;

    beforeEach(() => {
      mockDialogRef = { afterClosed: jest.fn() };
      dialogServiceMock.openDialog.mockReturnValue(mockDialogRef);
      jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    });

    it("should open SaveAndExit dialog when there are changes", () => {
      mockDialogRef.afterClosed.mockReturnValue(of(undefined));
      component.privacyideaForm.description().markAsDirty();
      component.onCancel();
      expect(dialogServiceMock.openDialog).toHaveBeenCalledWith(
        expect.objectContaining({ component: SaveAndExitDialogComponent })
      );
    });

    it("should navigate after 'discard'", async () => {
      mockDialogRef.afterClosed.mockReturnValue(of("discard"));
      component.privacyideaForm.description().markAsDirty();
      component.onCancel();
      await new Promise((r) => setTimeout(r, 0));
      expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
    });

    it("should save and navigate when 'save-exit' selected and save succeeds", async () => {
      mockDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      const pcs = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      pcs.save = jest.fn().mockReturnValue(Promise.resolve(true));
      component.privacyideaModel.update((m) => ({ ...m, identifier: "x", url: "http://x" }));
      component.privacyideaForm.description().markAsDirty();
      component.onCancel();
      await new Promise((r) => setTimeout(r, 0));
      expect(pcs.save).toHaveBeenCalled();
    });

    it("should not navigate when 'save-exit' but canSave is false", async () => {
      mockDialogRef.afterClosed.mockReturnValue(of("save-exit"));
      const pcs = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
      pcs.save = jest.fn();
      component.privacyideaModel.update((m) => ({ ...m, identifier: "", url: "" }));
      component.privacyideaForm.description().markAsDirty();
      component.onCancel();
      await new Promise((r) => setTimeout(r, 0));
      expect(pcs.save).not.toHaveBeenCalled();
    });
  });
});
