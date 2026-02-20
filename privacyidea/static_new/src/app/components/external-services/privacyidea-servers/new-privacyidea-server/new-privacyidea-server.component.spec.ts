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
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from "@angular/material/dialog";
import { Subject } from "rxjs";
import { PrivacyideaServerService } from "../../../../services/privacyidea-server/privacyidea-server.service";
import { MockPrivacyideaServerService } from "../../../../../testing/mock-services/mock-privacyidea-server-service";
import { MockDialogService } from "../../../../../testing/mock-services";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { SaveAndExitDialogResult } from "../../../shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { MockMatDialogRef } from "../../../../../testing/mock-mat-dialog-ref";

describe("NewPrivacyideaServerComponent", () => {
  let component: NewPrivacyideaServerComponent;
  let fixture: ComponentFixture<NewPrivacyideaServerComponent>;
  let privacyideaServerServiceMock: any;
  let dialogRefMock: MockMatDialogRef<any, any>;
  let confirmClosed: Subject<SaveAndExitDialogResult>;
  let dialogServiceMock: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewPrivacyideaServerComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: null },
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: PrivacyideaServerService, useClass: MockPrivacyideaServerService },
        { provide: DialogService, useClass: MockDialogService }
      ]
    }).compileComponents();

    privacyideaServerServiceMock = TestBed.inject(PrivacyideaServerService);

    fixture = TestBed.createComponent(NewPrivacyideaServerComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    confirmClosed = new Subject();
    dialogRefMock = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<any, any>;
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
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

  it("should initialize form for edit mode", async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [NewPrivacyideaServerComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MAT_DIALOG_DATA, useValue: { identifier: "test", url: "http://test", tls: true } },
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: PrivacyideaServerService, useClass: MockPrivacyideaServerService }
      ]
    })
      .overrideComponent(NewPrivacyideaServerComponent, {
        add: {
          providers: [{ provide: DialogService, useClass: MockDialogService }]
        }
      })
      .compileComponents();

    privacyideaServerServiceMock = TestBed.inject(PrivacyideaServerService);

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
    component.privacyideaForm.patchValue({ identifier: "test", url: "http://test" });
    component.save();
    expect(privacyideaServerServiceMock.postPrivacyideaServer).toHaveBeenCalled();
    confirmClosed.next("save-exit");
    confirmClosed.complete();
    expect(dialogRefMock.close).toHaveBeenCalledWith(true);
  });

  it("should call test when form is valid", async () => {
    component.privacyideaForm.patchValue({ identifier: "test", url: "http://test" });
    component.test();
    expect(privacyideaServerServiceMock.testPrivacyideaServer).toHaveBeenCalled();
  });

  it("should close dialog on cancel without changes", () => {
    component.onCancel();
    confirmClosed.next("discard");
    confirmClosed.complete();
    expect(dialogRefMock.close).toHaveBeenCalled();
  });

  it("should show confirmation dialog on cancel with changes", () => {
    component.privacyideaForm.get("description")?.markAsDirty();
    component.onCancel();
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
  });
});
