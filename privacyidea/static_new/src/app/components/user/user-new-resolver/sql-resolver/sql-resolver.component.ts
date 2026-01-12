import { Component, effect, EventEmitter, input, OnInit, Output } from "@angular/core";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatHint, MatInput } from "@angular/material/input";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { MatCheckbox } from "@angular/material/checkbox";
import { SQLResolverData } from "../../../../services/resolver/resolver.service";

@Component({
  selector: "app-sql-resolver",
  standalone: true,
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    ReactiveFormsModule,
    MatInput,
    MatCheckbox,
    MatHint,
    MatError
  ],
  templateUrl: "./sql-resolver.component.html",
  styleUrl: "./sql-resolver.component.scss"
})
export class SqlResolverComponent implements OnInit {
  data = input<Partial<SQLResolverData>>({});
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();

  driverControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  serverControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  tableControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  limitControl = new FormControl<number | undefined>(undefined, {
    validators: [Validators.required]
  });
  mapControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });

  constructor() {
    effect(() => {
      const initial = this.data();
      if (initial.Driver !== undefined) {
        this.driverControl.setValue(initial.Driver, { emitEvent: false });
      }
      if (initial.Server !== undefined) {
        this.serverControl.setValue(initial.Server, { emitEvent: false });
      }
      if (initial.Table !== undefined) {
        this.tableControl.setValue(initial.Table, { emitEvent: false });
      }
      if (initial.Limit !== undefined) {
        this.limitControl.setValue(initial.Limit, { emitEvent: false });
      }
      if (initial.Map !== undefined) {
        this.mapControl.setValue(initial.Map, { emitEvent: false });
      }
    });
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      Driver: this.driverControl,
      Server: this.serverControl,
      Table: this.tableControl,
      Limit: this.limitControl,
      Map: this.mapControl
    });
  }

}
