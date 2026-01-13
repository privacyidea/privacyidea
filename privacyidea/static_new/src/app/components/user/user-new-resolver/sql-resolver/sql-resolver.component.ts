import { Component, computed, effect, input } from "@angular/core";
import { AbstractControl, FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
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
export class SqlResolverComponent {
  data = input<Partial<SQLResolverData>>({});

  driverControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  serverControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  tableControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });
  limitControl = new FormControl<number | undefined>(undefined, { validators: [Validators.required] });
  mapControl = new FormControl<string>("", { nonNullable: true, validators: [Validators.required] });

  databaseControl = new FormControl<string>("", { nonNullable: true });
  portControl = new FormControl<number | undefined>(undefined);
  userControl = new FormControl<string>("", { nonNullable: true });
  passwordControl = new FormControl<string>("", { nonNullable: true });
  passwordHashTypeControl = new FormControl<string>("plain", { nonNullable: true });
  poolSizeControl = new FormControl<number>(5, { nonNullable: true });
  poolTimeoutControl = new FormControl<number>(10, { nonNullable: true });
  poolRecycleControl = new FormControl<number>(7200, { nonNullable: true });
  editableControl = new FormControl<boolean>(false, { nonNullable: true });
  conParamsControl = new FormControl<string>("", { nonNullable: true });
  encodingControl = new FormControl<string>("", { nonNullable: true });
  whereControl = new FormControl<string>("", { nonNullable: true });

  controls = computed<Record<string, AbstractControl>>(() => ({
    Driver: this.driverControl,
    Server: this.serverControl,
    Table: this.tableControl,
    Limit: this.limitControl,
    Map: this.mapControl,
    Database: this.databaseControl,
    Port: this.portControl,
    User: this.userControl,
    Password: this.passwordControl,
    Password_Hash_Type: this.passwordHashTypeControl,
    poolSize: this.poolSizeControl,
    poolTimeout: this.poolTimeoutControl,
    poolRecycle: this.poolRecycleControl,
    Editable: this.editableControl,
    conParams: this.conParamsControl,
    Encoding: this.encodingControl,
    Where: this.whereControl
  }));

  constructor() {
    effect(() => {
      const initial = this.data();
      if (initial.Driver !== undefined) this.driverControl.setValue(initial.Driver, { emitEvent: false });
      if (initial.Server !== undefined) this.serverControl.setValue(initial.Server, { emitEvent: false });
      if (initial.Table !== undefined) this.tableControl.setValue(initial.Table, { emitEvent: false });
      if (initial.Limit !== undefined) this.limitControl.setValue(initial.Limit, { emitEvent: false });
      if (initial.Map !== undefined) this.mapControl.setValue(initial.Map, { emitEvent: false });

      if (initial.Database !== undefined) this.databaseControl.setValue(initial.Database, { emitEvent: false });
      if (initial.Port !== undefined) this.portControl.setValue(initial.Port, { emitEvent: false });
      if (initial.User !== undefined) this.userControl.setValue(initial.User, { emitEvent: false });
      if (initial.Password !== undefined) this.passwordControl.setValue(initial.Password, { emitEvent: false });
      if (initial.Password_Hash_Type !== undefined) this.passwordHashTypeControl.setValue(initial.Password_Hash_Type, { emitEvent: false });
      if (initial.poolSize !== undefined) this.poolSizeControl.setValue(initial.poolSize, { emitEvent: false });
      if (initial.poolTimeout !== undefined) this.poolTimeoutControl.setValue(initial.poolTimeout, { emitEvent: false });
      if (initial.poolRecycle !== undefined) this.poolRecycleControl.setValue(initial.poolRecycle, { emitEvent: false });
      if (initial.Editable !== undefined) this.editableControl.setValue(initial.Editable, { emitEvent: false });
      if (initial.conParams !== undefined) this.conParamsControl.setValue(initial.conParams, { emitEvent: false });
      if (initial.Encoding !== undefined) this.encodingControl.setValue(initial.Encoding, { emitEvent: false });
      if (initial.Where !== undefined) this.whereControl.setValue(initial.Where, { emitEvent: false });
    });
  }
}
