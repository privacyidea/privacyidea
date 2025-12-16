import { Component, EventEmitter, Input, Output } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { MatHint, MatInput } from "@angular/material/input";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { PasswdResolverData, SQLResolverData } from "../../../../services/resolver/resolver.service";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatDivider } from "@angular/material/list";

@Component({
  selector: 'app-sql-resolver',
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    MatInput,
    MatCheckbox,
    MatHint,
    MatDivider
  ],
  templateUrl: './sql-resolver.component.html',
  styleUrl: './sql-resolver.component.scss'
})
export class SqlResolverComponent {
  @Input() data: Partial<SQLResolverData> = {};
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();

}
