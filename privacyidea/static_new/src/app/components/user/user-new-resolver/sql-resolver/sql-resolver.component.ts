import { Component, EventEmitter, Input, Output } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { MatInput } from "@angular/material/input";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { PasswdResolverData } from "../../../../services/resolver/resolver.service";

@Component({
  selector: 'app-sql-resolver',
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    MatInput
  ],
  templateUrl: './sql-resolver.component.html',
  styleUrl: './sql-resolver.component.scss'
})
export class SqlResolverComponent {
  @Input() data: Partial<PasswdResolverData & { Filename?: string }> = {};
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();

}
