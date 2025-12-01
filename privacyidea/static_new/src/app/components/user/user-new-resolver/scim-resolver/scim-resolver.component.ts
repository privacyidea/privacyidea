import { Component, EventEmitter, Input, Output } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { PasswdResolverData } from "../../../../services/resolver/resolver.service";

@Component({
  selector: 'app-scim-resolver',
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    MatInput
  ],
  templateUrl: './scim-resolver.component.html',
  styleUrl: './scim-resolver.component.scss'
})
export class ScimResolverComponent {
  @Input() data: Partial<PasswdResolverData & { Filename?: string }> = {};
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();

}
