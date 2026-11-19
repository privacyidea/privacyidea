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

import { SaveAndExitDialogResult } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockTokenService } from "@testing/mock-services";
import { MockDialogService } from "@testing/mock-services/mock-dialog-service";
import { lastValueFrom, of, throwError } from "rxjs";
import { ENROLLMENT_CANCELLED } from "@components/token/token-enrollment/token-enrollment.constants";
import { confirmLeaveIncompleteStep, leaveIncompleteEnrollment } from "./leave-incomplete-enrollment";

describe("leaveIncompleteEnrollment", () => {
  let dialogService: MockDialogService;
  let tokenService: MockTokenService;

  const answer = (result: SaveAndExitDialogResult | undefined) => {
    const dialogRef = new MockMatDialogRef();
    dialogRef.afterClosed.mockReturnValue(of(result));
    dialogService.openDialog.mockReturnValue(dialogRef);
  };

  const leave = () => lastValueFrom(leaveIncompleteEnrollment(dialogService, tokenService, "HOTP0001"));

  beforeEach(() => {
    dialogService = new MockDialogService();
    tokenService = new MockTokenService();
  });

  it("offers to keep or delete the token", async () => {
    answer(undefined);
    await leave();

    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          saveButtonText: "Keep Token",
          discardButtonText: "Delete Token",
          cancelButtonText: "Back"
        })
      })
    );
  });

  it("keeps the token", async () => {
    answer("save-exit");

    expect(await leave()).toBe("keep");
    expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
  });

  it("deletes the token", async () => {
    answer("discard");

    expect(await leave()).toBe("deleted");
    expect(tokenService.cancelEnrollment).toHaveBeenCalledWith("HOTP0001");
  });

  it("stays when the dialog is cancelled", async () => {
    answer(undefined);

    expect(await leave()).toBe("stay");
    expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
  });

  it("stays when the token cannot be deleted", async () => {
    answer("discard");
    tokenService.cancelEnrollment.mockReturnValue(throwError(() => new Error("denied")));

    expect(await leave()).toBe("stay");
  });

  describe("confirmLeaveIncompleteStep", () => {
    let close: jest.Mock;
    const confirmLeave = (canCancel: boolean) =>
      confirmLeaveIncompleteStep({
        dialogService,
        tokenService,
        serial: () => "HOTP0001",
        canCancel: () => canCancel,
        close
      });

    beforeEach(() => {
      close = jest.fn();
    });

    it("closes and follows the link without asking while Close is offered", async () => {
      expect(await lastValueFrom(confirmLeave(false)("token"))).toBe(true);
      expect(dialogService.openDialog).not.toHaveBeenCalled();
      expect(close).toHaveBeenCalledWith();
    });

    it("closes and follows the link when the token is kept", async () => {
      answer("save-exit");

      expect(await lastValueFrom(confirmLeave(true)("token"))).toBe(true);
      expect(close).toHaveBeenCalledWith();
    });

    it("does not open the details of the deleted token", async () => {
      answer("discard");

      expect(await lastValueFrom(confirmLeave(true)("token"))).toBe(false);
      expect(close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });

    it("follows a link to another page after deleting the token", async () => {
      answer("discard");

      expect(await lastValueFrom(confirmLeave(true)("user"))).toBe(true);
      expect(close).toHaveBeenCalledWith(ENROLLMENT_CANCELLED);
    });

    it("neither closes nor follows the link when the user stays", async () => {
      answer(undefined);

      expect(await lastValueFrom(confirmLeave(true)("token"))).toBe(false);
      expect(close).not.toHaveBeenCalled();
    });
  });
});
