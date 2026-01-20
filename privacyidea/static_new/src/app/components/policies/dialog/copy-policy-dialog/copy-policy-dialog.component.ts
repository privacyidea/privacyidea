import { Component } from "@angular/core";
import { DialogWrapperComponent } from "../../../shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { CommonModule } from "@angular/common";
import { DialogAction } from "../../../../models/dialog";
import { AbstractDialogComponent } from "../../../shared/dialog/abstract-dialog/abstract-dialog.component";
import {
  AbstractControl,
  FormControl,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators
} from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { toSignal } from "@angular/core/rxjs-interop";
import { map } from "rxjs";
export function mustBeDifferentValidator(originalValue: string | null): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const isSame = control.value === originalValue;
    return isSame ? { notChanged: true } : null;
  };
}
@Component({
  selector: "app-copy-policy-dialog",
  templateUrl: "./copy-policy-dialog.component.html",
  styleUrls: ["./copy-policy-dialog.component.scss"],
  standalone: true,
  imports: [DialogWrapperComponent, CommonModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule]
})
export class CopyPolicyDialogComponent extends AbstractDialogComponent<string, string | null> {
  nameControl = new FormControl(this.data, [Validators.required, mustBeDifferentValidator(this.data)]);

  isInvalid = toSignal(
    this.nameControl.statusChanges.pipe(
      map(() => {
        console.log("Name control status:", this.nameControl.status);
        return this.nameControl.invalid;
      })
    ),
    {
      initialValue: (() => {
        console.log("Initial name control status:", this.nameControl.status);
        return this.nameControl.invalid;
      })()
    }
  );

  actions: DialogAction<"submit" | null>[] = [
    {
      label: "Copy Policy",
      value: "submit",
      type: "confirm",
      disabled: () => {
        console.log("Is invalid:", this.isInvalid());
        return this.isInvalid();
      }
    }
  ];

  onAction(value: "submit" | null): void {
    if (value === "submit" && this.nameControl.valid) {
      this.close(this.nameControl.value);
    } else {
      this.close(null);
    }
  }
}
