import { Component, model } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatInputModule } from "@angular/material/input";
import { ClearableInputComponent } from "../../../shared/clearable-input/clearable-input.component";

@Component({
  selector: "app-container-templates-filter",
  standalone: true,
  imports: [FormsModule, MatInputModule, ClearableInputComponent],
  templateUrl: "./container-templates-filter.component.html",
  styleUrl: "./container-templates-filter.component.scss"
})
export class ContainerTemplatesFilterComponent {
  readonly filter = model<string>("");
}
