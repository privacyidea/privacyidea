import { DialogServiceInterface } from "../../app/services/dialog/dialog.service";
import { signal } from "@angular/core";

export class MockDialogService implements DialogServiceInterface {
  isSelfServing = signal<boolean>(false);
  tokenEnrollmentFirstStepRef = null;
  isTokenEnrollmentFirstStepDialogOpen = false;
  tokenEnrollmentLastStepRef = null;
  isTokenEnrollmentLastStepDialogOpen = false;
  openTokenEnrollmentFirstStepDialog = jest.fn().mockReturnValue(undefined);
  closeTokenEnrollmentFirstStepDialog = jest.fn().mockReturnValue(undefined);
  openTokenEnrollmentLastStepDialog = jest.fn().mockReturnValue(undefined);
  closeTokenEnrollmentLastStepDialog = jest.fn().mockReturnValue(undefined);
  confirm = jest.fn().mockResolvedValue(true);
  isAnyDialogOpen = jest.fn().mockReturnValue(false);
}
