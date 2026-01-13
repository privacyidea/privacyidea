import { Component, Input } from "@angular/core";
import { FormGroup, ReactiveFormsModule } from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatSelectModule } from "@angular/material/select";
import { MatCheckboxModule } from "@angular/material/checkbox";

@Component({
  selector: "app-http-config",
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule
  ],
  templateUrl: "./http-config.component.html",
  styleUrl: "./http-config.component.scss"
})
export class HttpConfigComponent {
  @Input({ required: true }) formGroup!: FormGroup;
  @Input({ required: true }) title!: string;
  @Input() description?: string;
  @Input() endpointHint?: string;

}
