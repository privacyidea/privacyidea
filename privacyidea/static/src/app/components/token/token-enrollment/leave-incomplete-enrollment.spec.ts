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
import { lastValueFrom, NEVER, of, Subject, throwError } from "rxjs";
import { leaveIncompleteEnrollment } from "./leave-incomplete-enrollment";

describe("leaveIncompleteEnrollment", () => {
  let dialogService: MockDialogService;
  let tokenService: MockTokenService;

  const answer = (result: SaveAndExitDialogResult | undefined) => {
    const dialogRef = new MockMatDialogRef();
    dialogRef.afterClosed.mockReturnValue(of(result));
    dialogService.openDialog.mockReturnValue(dialogRef);
  };

  const leave = () => lastValueFrom(leaveIncompleteEnrollment(dialogService, tokenService, "HOTP0001", NEVER));

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

  it("closes the question and stays when the step closes by itself", async () => {
    const stepClosed = new Subject<void>();
    const result = lastValueFrom(leaveIncompleteEnrollment(dialogService, tokenService, "HOTP0001", stepClosed));
    const questionRef = dialogService.openDialog.mock.results[0].value as MockMatDialogRef<unknown>;

    stepClosed.next();

    expect(questionRef.close).toHaveBeenCalled();
    expect(await result).toBe("stay");
    expect(tokenService.cancelEnrollment).not.toHaveBeenCalled();
  });

  it("stays when the token cannot be deleted", async () => {
    answer("discard");
    tokenService.cancelEnrollment.mockReturnValue(throwError(() => new Error("denied")));

    expect(await leave()).toBe("stay");
  });

  it("adds what deleting means in the current step to the question", async () => {
    answer(undefined);
    await lastValueFrom(
      leaveIncompleteEnrollment(dialogService, tokenService, "PIPU0001", NEVER, "Scanned codes stop working.")
    );

    const message = dialogService.openDialog.mock.calls[0][0].data.message as string;
    expect(message).toMatch(/^The enrollment of this token is not complete\..* Scanned codes stop working\.$/);
  });
});
