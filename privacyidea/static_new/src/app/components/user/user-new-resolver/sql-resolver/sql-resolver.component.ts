import { Component, EventEmitter, Input, Output } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { MatHint, MatInput } from "@angular/material/input";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatCheckbox } from "@angular/material/checkbox";
import { SQLResolverData } from "../../../../services/resolver/resolver.service";

@Component({
  selector: "app-sql-resolver",
  standalone: true,
  imports: [
    MatFormField,
    MatLabel,
    FormsModule,
    MatInput,
    MatCheckbox,
    MatHint
  ],
  templateUrl: "./sql-resolver.component.html",
  styleUrl: "./sql-resolver.component.scss"
})
export class SqlResolverComponent {
  @Input() data: Partial<SQLResolverData> = {};
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();

}
