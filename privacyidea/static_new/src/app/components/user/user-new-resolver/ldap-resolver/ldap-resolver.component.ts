import { Component, EventEmitter, Input, Output } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { PasswdResolverData } from "../../../../services/resolver/resolver.service";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";

@Component({
  selector: 'app-ldap-resolver',
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    MatInput
  ],
  templateUrl: './ldap-resolver.component.html',
  styleUrl: './ldap-resolver.component.scss'
})
export class LdapResolverComponent {
  @Input() data: Partial<PasswdResolverData & { Filename?: string }> = {};
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();

}
