import { MatDialogRef } from "@angular/material/dialog";
import { of } from "rxjs";

export class MockMatDialogRef<T, R = any> implements Partial<MatDialogRef<T, R>> {
  close = jest.fn();
  afterClosed = jest.fn().mockReturnValue(of(undefined));
  afterOpened = jest.fn().mockReturnValue(of(undefined));
  backdropClick = jest.fn().mockReturnValue(of(new MouseEvent("click")));
  keydownEvents = jest.fn().mockReturnValue(of(new KeyboardEvent("keydown")));
  updateSize = jest.fn().mockReturnThis();
  updatePosition = jest.fn().mockReturnThis();
}
