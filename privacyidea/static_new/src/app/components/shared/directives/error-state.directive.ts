import { Directive, effect, inject, input } from "@angular/core";
import { MatFormFieldControl } from "@angular/material/form-field";
import { Subject } from "rxjs";

@Directive({
  selector: "[appErrorState]",
  standalone: true
})
export class ErrorStateDirective {
  appErrorState = input.required<boolean>();

  private readonly control = inject<MatFormFieldControl<unknown> | null>(MatFormFieldControl as never, {
    self: true,
    optional: true
  });

  constructor() {
    if (!this.control) return;
    effect(() => {
      const show = this.appErrorState();
      const control = this.control as unknown as { errorState: boolean; stateChanges: Subject<void> };
      control.errorState = show;
      control.stateChanges.next();
    });
  }
}
