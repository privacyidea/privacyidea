import { Component, EventEmitter, Input, Output, signal, WritableSignal } from "@angular/core";
import { MatFormField, MatHint, MatInput, MatLabel } from "@angular/material/input";
import { SQLResolverData } from "../../../../services/resolver/resolver.service";
import { FormControl, FormsModule } from "@angular/forms";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatCheckbox } from "@angular/material/checkbox";
import { MatSlideToggle } from "@angular/material/slide-toggle";

@Component({
  selector: 'app-http-resolver',
  imports: [
    MatFormField,
    MatLabel,
    MatInput,
    FormsModule,
    MatSelect,
    MatOption,
    MatCheckbox,
    MatSlideToggle,
    MatHint
  ],
  templateUrl: './http-resolver.component.html',
  styleUrl: './http-resolver.component.scss'
})
export class HttpResolverComponent {
  @Input() data: Partial<SQLResolverData> = {};
  @Output() additionalFormFieldsChange = new EventEmitter<{ [key: string]: FormControl<any> }>();
  protected basicSettings: WritableSignal<boolean> = signal(true);

}
