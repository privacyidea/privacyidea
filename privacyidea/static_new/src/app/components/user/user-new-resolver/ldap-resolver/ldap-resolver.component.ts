import { Component, EventEmitter, input, Output } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatOption } from "@angular/material/core";
import { MatCheckboxModule } from "@angular/material/checkbox";
import { LDAPResolverData } from "../../../../services/resolver/resolver.service";

@Component({
  selector: "app-ldap-resolver",
  standalone: true,
  imports: [
    FormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatSelectModule,
    MatSelect,
    MatOption,
    MatCheckboxModule
  ],
  templateUrl: "./ldap-resolver.component.html",
  styleUrl: "./ldap-resolver.component.scss"
})
export class LdapResolverComponent {
  data = input<Partial<LDAPResolverData>>({});
  @Output() additionalFormFieldsChange =
    new EventEmitter<{ [key: string]: FormControl<any> }>();
}
