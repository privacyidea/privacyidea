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
import { TestBed } from "@angular/core/testing";
import { Subject } from "rxjs";
import { MatDialog, MatDialogRef } from "@angular/material/dialog";
import { DialogService } from "./dialog.service";
import { Component } from "@angular/core";
import { AbstractDialogComponent } from "../../components/shared/dialog/abstract-dialog/abstract-dialog.component";

@Component({ template: "" })
class TestDialogComponent extends AbstractDialogComponent<any, any> {}

const matDialogMock = {
  openDialogs: [] as MatDialogRef<any>[],
  open: jest.fn(),
  closeAll: jest.fn()
};

describe("DialogService", () => {
  let service: DialogService;
  let matDialog: MatDialog;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: MatDialog, useValue: matDialogMock }]
    });
    service = TestBed.inject(DialogService);
    matDialog = TestBed.inject(MatDialog);
    // Reset mocks before each test
    matDialogMock.open.mockClear();
    matDialogMock.closeAll.mockClear();
    matDialogMock.openDialogs = [];
    service.openDialogs.clear();
  });

  it("should be created", () => {
    expect(service).toBeTruthy();
  });

  describe("openDialog", () => {
    it("should open a dialog and add it to the openDialogs set", () => {
      const afterClosed$ = new Subject<void>();
      const mockDialogRef = {
        afterClosed: () => afterClosed$.asObservable()
      } as MatDialogRef<any>;
      matDialogMock.open.mockReturnValue(mockDialogRef);

      const dialogRef = service.openDialog({ component: TestDialogComponent });

      expect(matDialog.open).toHaveBeenCalledWith(TestDialogComponent, {
        disableClose: false,
        hasBackdrop: true,
        data: undefined
      });
      expect(dialogRef).toBe(mockDialogRef);
      expect(service.openDialogs.has(mockDialogRef)).toBe(true);
    });

    it("should remove the dialog from the set after it is closed", () => {
      const afterClosed$ = new Subject<void>();
      const mockDialogRef = {
        afterClosed: () => afterClosed$.asObservable()
      } as MatDialogRef<any>;
      matDialogMock.open.mockReturnValue(mockDialogRef);

      service.openDialog({ component: TestDialogComponent });
      expect(service.openDialogs.has(mockDialogRef)).toBe(true);

      afterClosed$.next();
      afterClosed$.complete();

      expect(service.openDialogs.has(mockDialogRef)).toBe(false);
    });

    it("should override default config", () => {
      const afterClosed$ = new Subject<void>();
      const mockDialogRef = {
        afterClosed: () => afterClosed$.asObservable()
      } as MatDialogRef<any>;
      matDialogMock.open.mockReturnValue(mockDialogRef);

      service.openDialog({
        component: TestDialogComponent,
        data: { test: "data" },
        configOverride: { disableClose: true }
      });

      expect(matDialog.open).toHaveBeenCalledWith(TestDialogComponent, {
        disableClose: true,
        hasBackdrop: true,
        data: { test: "data" }
      });
    });
  });

  describe("closeDialog", () => {
    it("should close the dialog if it is open", () => {
      const mockDialogRef = {
        close: jest.fn()
      } as unknown as MatDialogRef<any>;
      service.openDialogs.add(mockDialogRef);

      const result = service.closeDialog(mockDialogRef, "test");

      expect(mockDialogRef.close).toHaveBeenCalledWith("test");
      expect(result).toBe(true);
    });

    it("should not close the dialog if it is not open", () => {
      const mockDialogRef = {
        close: jest.fn()
      } as unknown as MatDialogRef<any>;

      const result = service.closeDialog(mockDialogRef);

      expect(mockDialogRef.close).not.toHaveBeenCalled();
      expect(result).toBe(false);
    });
  });

  describe("closeLatestDialog", () => {
    it("should close the most recently opened dialog", () => {
      const firstDialogRef = { close: jest.fn() } as unknown as MatDialogRef<any>;
      const secondDialogRef = { close: jest.fn() } as unknown as MatDialogRef<any>;
      service.openDialogs.add(firstDialogRef);
      service.openDialogs.add(secondDialogRef);

      service.closeLatestDialog();

      expect(firstDialogRef.close).not.toHaveBeenCalled();
      expect(secondDialogRef.close).toHaveBeenCalled();
    });

    it("should do nothing if no dialogs are open", () => {
      // No spy needed, just ensuring no error is thrown
      service.closeLatestDialog();
      expect(true).toBe(true); // To avoid empty test
    });
  });

  describe("closeAllDialogs", () => {
    it("should call MatDialog.closeAll and clear the openDialogs set", () => {
      service.openDialogs.add({} as MatDialogRef<any>);
      expect(service.openDialogs.size).toBe(1);

      service.closeAllDialogs();

      expect(matDialog.closeAll).toHaveBeenCalled();
      expect(service.openDialogs.size).toBe(0);
    });
  });

  describe("isDialogOpen", () => {
    it("should return true if the dialog is in the openDialogs set", () => {
      const mockDialogRef = {} as MatDialogRef<any>;
      service.openDialogs.add(mockDialogRef);
      expect(service.isDialogOpen(mockDialogRef)).toBe(true);
    });

    it("should return false if the dialog is not in the openDialogs set", () => {
      const mockDialogRef = {} as MatDialogRef<any>;
      expect(service.isDialogOpen(mockDialogRef)).toBe(false);
    });
  });

  describe("isAnyDialogOpen", () => {
    it("should return true if MatDialog.openDialogs has open dialogs", () => {
      matDialogMock.openDialogs = [{} as MatDialogRef<any>];
      expect(service.isAnyDialogOpen()).toBe(true);
    });

    it("should return false if MatDialog.openDialogs is empty", () => {
      matDialogMock.openDialogs = [];
      expect(service.isAnyDialogOpen()).toBe(false);
    });
  });
});
