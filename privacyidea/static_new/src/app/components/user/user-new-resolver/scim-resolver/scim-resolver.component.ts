import { Component, effect, EventEmitter, input, OnInit, Output } from "@angular/core";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
import { SCIMResolverData } from "../../../../services/resolver/resolver.service";

@Component({
  selector: "app-scim-resolver",
  standalone: true,
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    ReactiveFormsModule,
    MatInput,
    MatError
  ],
  templateUrl: './scim-resolver.component.html',
  styleUrl: './scim-resolver.component.scss'
})
export class ScimResolverComponent implements OnInit {
  data = input<Partial<SCIMResolverData>>({});
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();

  authServerControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  resourceServerControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  clientControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  secretControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  mappingControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });

  constructor() {
    effect(() => {
      const initial = this.data();
      if (initial.Authserver !== undefined) {
        this.authServerControl.setValue(initial.Authserver, { emitEvent: false });
      }
      if (initial.Resourceserver !== undefined) {
        this.resourceServerControl.setValue(initial.Resourceserver, { emitEvent: false });
      }
      if (initial.Client !== undefined) {
        this.clientControl.setValue(initial.Client, { emitEvent: false });
      }
      if (initial.Secret !== undefined) {
        this.secretControl.setValue(initial.Secret, { emitEvent: false });
      }
      if (initial.Mapping !== undefined) {
        this.mappingControl.setValue(initial.Mapping, { emitEvent: false });
      }
    });
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      Authserver: this.authServerControl,
      Resourceserver: this.resourceServerControl,
      Client: this.clientControl,
      Secret: this.secretControl,
      Mapping: this.mappingControl
    });
  }

}
