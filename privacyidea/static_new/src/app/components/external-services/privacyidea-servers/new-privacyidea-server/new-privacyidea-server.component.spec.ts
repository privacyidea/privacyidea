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
import { NewPrivacyideaServerComponent } from "./new-privacyidea-server.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ActivatedRoute, convertToParamMap, ParamMap, provideRouter, Router } from "@angular/router";
import { BehaviorSubject } from "rxjs";
import { PrivacyideaServerService } from "../../../../services/privacyidea-server/privacyidea-server.service";
import { MockPrivacyideaServerService } from "../../../../../testing/mock-services/mock-privacyidea-server-service";
import { MockDialogService } from "../../../../../testing/mock-services";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { ROUTE_PATHS } from "../../../../route_paths";
import { signal } from "@angular/core";

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
      imports: [NewPrivacyideaServerComponent, NoopAnimationsModule],
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
    expect(component.isEditMode).toBe(false);
    expect(component.privacyideaForm.get("identifier")?.value).toBe("");
  });

  it("should initialize form for edit mode", () => {
    privacyideaServerServiceMock.remoteServerOptions = signal([
      { identifier: "test", url: "http://test", tls: true }
    ]);

    paramMapSubject.next(convertToParamMap({ identifier: "test" }));

    fixture.destroy();
    fixture = TestBed.createComponent(NewPrivacyideaServerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isEditMode).toBe(true);
    expect(component.privacyideaForm.get("identifier")?.value).toBe("test");
    expect(component.privacyideaForm.get("identifier")?.disabled).toBe(true);
  });

  it("should be invalid when required fields are missing", () => {
    component.privacyideaForm.patchValue({ identifier: "", url: "" });
    expect(component.privacyideaForm.valid).toBe(false);
  });

  it("should call save when form is valid", async () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.privacyideaForm.patchValue({ identifier: "test", url: "http://test" });
    const success = await component.save();
    expect(success).toBe(true);
    expect(privacyideaServerServiceMock.postPrivacyideaServer).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
  });

  it("save should return false on error", async () => {
    component.privacyideaForm.patchValue({ identifier: "test", url: "http://test" });
    privacyideaServerServiceMock.postPrivacyideaServer = jest.fn().mockRejectedValue(new Error("post-failed"));

    const success = await component.save();
    expect(success).toBe(false);
    expect(privacyideaServerServiceMock.postPrivacyideaServer).toHaveBeenCalled();
  });

  it("should call test when form is valid", async () => {
    component.privacyideaForm.patchValue({ identifier: "test", url: "http://test" });
    component.test();
    expect(privacyideaServerServiceMock.testPrivacyideaServer).toHaveBeenCalled();
  });

  it("should navigate back on cancel without changes", () => {
    const navigateSpy = jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    component.onCancel();
    expect(navigateSpy).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA);
  });

  it("should show confirmation dialog on cancel with changes", () => {
    component.privacyideaForm.get("description")?.markAsDirty();
    component.onCancel();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
  });
});
