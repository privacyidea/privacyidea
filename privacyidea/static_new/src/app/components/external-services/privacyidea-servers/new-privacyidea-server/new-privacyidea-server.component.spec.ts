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
import { DialogService } from "@services/dialog/dialog.service";
import { PrivacyideaServerService } from "@services/privacyidea-server/privacyidea-server.service";
import { MockDialogService, MockPrivacyideaServerService } from "@testing/mock-services";
import { BehaviorSubject } from "rxjs";
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
        { provide: DialogService, useClass: MockDialogService },
        { provide: ActivatedRoute, useValue: { paramMap: paramMapSubject.asObservable() } }
      ]
    }).compileComponents();

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
});
