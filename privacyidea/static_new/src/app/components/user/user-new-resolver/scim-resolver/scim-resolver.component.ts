import { Component, EventEmitter, Input, Output } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { SCIMResolverData } from "../../../../services/resolver/resolver.service";

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
  @Input() data: Partial<SCIMResolverData> = {};
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();

}
