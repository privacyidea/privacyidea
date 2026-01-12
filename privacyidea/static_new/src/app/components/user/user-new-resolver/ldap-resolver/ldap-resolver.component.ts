import { Component, effect, EventEmitter, input, OnInit, Output } from "@angular/core";
import { FormControl, FormsModule, ReactiveFormsModule, Validators } from "@angular/forms";
import { MatError, MatFormField, MatLabel } from "@angular/material/form-field";
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
    ReactiveFormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatError,
    MatSelectModule,
    MatSelect,
    MatOption,
    MatCheckboxModule
  ],
  templateUrl: "./ldap-resolver.component.html",
  styleUrl: "./ldap-resolver.component.scss"
})
export class LdapResolverComponent implements OnInit {
  data = input<Partial<LDAPResolverData>>({});
  @Output() additionalFormFieldsChange =
    new EventEmitter<{ [key: string]: FormControl<any> }>();

  ldapUriControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  ldapBaseControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  loginNameAttributeControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  ldapSearchFilterControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });
  userInfoControl = new FormControl<string>("", {
    nonNullable: true,
    validators: [Validators.required]
  });

  constructor() {
    effect(() => {
      const initial = this.data();
      if (initial.LDAPURI !== undefined) {
        this.ldapUriControl.setValue(initial.LDAPURI, { emitEvent: false });
      }
      if (initial.LDAPBASE !== undefined) {
        this.ldapBaseControl.setValue(initial.LDAPBASE, { emitEvent: false });
      }
      if (initial.LOGINNAMEATTRIBUTE !== undefined) {
        this.loginNameAttributeControl.setValue(initial.LOGINNAMEATTRIBUTE, { emitEvent: false });
      }
      if (initial.LDAPSEARCHFILTER !== undefined) {
        this.ldapSearchFilterControl.setValue(initial.LDAPSEARCHFILTER, { emitEvent: false });
      }
      if (initial.USERINFO !== undefined) {
        this.userInfoControl.setValue(initial.USERINFO, { emitEvent: false });
      }
    });
  }

  ngOnInit(): void {
    this.additionalFormFieldsChange.emit({
      LDAPURI: this.ldapUriControl,
      LDAPBASE: this.ldapBaseControl,
      LOGINNAMEATTRIBUTE: this.loginNameAttributeControl,
      LDAPSEARCHFILTER: this.ldapSearchFilterControl,
      USERINFO: this.userInfoControl
    });
  }
}
