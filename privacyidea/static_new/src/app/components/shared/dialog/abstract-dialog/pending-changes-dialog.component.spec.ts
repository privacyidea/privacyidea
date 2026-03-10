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

import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { Subject } from "rxjs";
import { DialogService } from "src/app/services/dialog/dialog.service";
import { PendingChangesService } from "src/app/services/pending-changes/pending-changes.service";
import { PendingChangesDialogComponent } from "./pending-changes-dialog.component";
import { MockDialogService, MockPendingChangesService } from "src/testing/mock-services";
import { MockMatDialogRef } from "src/testing/mock-mat-dialog-ref";

@Component({
  template: "",
  standalone: true
})
class TestDialogComponent extends PendingChangesDialogComponent<any, any> {
  readonly canSave = signal(true);
  readonly isDirty = signal(false);

  async onSave(): Promise<boolean> {
    return true;
  }
}

describe("PendingChangesDialogComponent", () => {
  let component: TestDialogComponent;
  let fixture: ComponentFixture<TestDialogComponent>;
  let dialogService: MockDialogService;
  let pendingChangesService: MockPendingChangesService;
  let dialogRef: MockMatDialogRef<any>;
  let backdropClick$: Subject<MouseEvent>;

  beforeEach(async () => {
    backdropClick$ = new Subject<MouseEvent>();

    await TestBed.configureTestingModule({
      imports: [TestDialogComponent],
      providers: [
        { provide: DialogService, useClass: MockDialogService },
        { provide: PendingChangesService, useClass: MockPendingChangesService },
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {} }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TestDialogComponent);
    component = fixture.componentInstance;

    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;
    pendingChangesService = TestBed.inject(PendingChangesService) as unknown as MockPendingChangesService;
    dialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<any>;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should register changes on init and unregister on destroy", () => {
    expect(pendingChangesService.registerHasChanges).toHaveBeenCalledWith(component.isDirty);

    component.ngOnDestroy();
    expect(pendingChangesService.unregisterHasChanges).toHaveBeenCalled();
  });

  it("should set disableClose to true on construction", () => {
    expect(dialogRef.disableClose).toBe(true);
  });

  it("should close directly if not dirty when backdrop is clicked", async () => {
    component.isDirty.set(false);

    backdropClick$.next(new MouseEvent("click"));

    expect(dialogRef.close).toHaveBeenCalled();
  });

  it("should open save-and-exit dialog if dirty and backdrop is clicked", async () => {
    component.isDirty.set(true);
    jest.spyOn(dialogService, "openDialogAsync").mockResolvedValue("discard");

    backdropClick$.next(new MouseEvent("click"));

    // Resolve openDialogAsync promise
    await Promise.resolve();

    expect(dialogService.openDialogAsync).toHaveBeenCalled();
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it("should call onSave and close if user selects save-exit and save is successful", async () => {
    component.isDirty.set(true);
    jest.spyOn(dialogService, "openDialogAsync").mockResolvedValue("save-exit");
    const onSaveSpy = jest.spyOn(component, "onSave").mockResolvedValue(true);

    backdropClick$.next(new MouseEvent("click"));

    // Wait for async step: openDialogAsync resolution
    await Promise.resolve();
    // Wait for async step: onSave resolution
    await Promise.resolve();

    expect(onSaveSpy).toHaveBeenCalled();
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it("should NOT close dialog if save fails on save-exit", async () => {
    component.isDirty.set(true);
    jest.spyOn(dialogService, "openDialogAsync").mockResolvedValue("save-exit");
    jest.spyOn(component, "onSave").mockResolvedValue(false);

    backdropClick$.next(new MouseEvent("click"));

    // Wait for async step: openDialogAsync resolution
    await Promise.resolve();

    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it("should do nothing if user cancels the save-and-exit dialog", async () => {
    component.isDirty.set(true);
    jest.spyOn(dialogService, "openDialogAsync").mockResolvedValue(undefined);

    backdropClick$.next(new MouseEvent("click"));

    // Wait for async step: openDialogAsync resolution
    await Promise.resolve();

    expect(dialogRef.close).not.toHaveBeenCalled();
  });
});
