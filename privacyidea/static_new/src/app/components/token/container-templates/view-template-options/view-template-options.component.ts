import { Component, input } from "@angular/core";
import { MatCardModule } from "@angular/material/card";
import { MatListModule } from "@angular/material/list";
import { CommonModule } from "@angular/common";

@Component({
  selector: "app-view-template-options",
  standalone: true,
  imports: [CommonModule, MatCardModule, MatListModule],
  templateUrl: "./view-template-options.component.html",
  styleUrl: "./view-template-options.component.scss"
})
export class ViewTemplateOptionsComponent {
  readonly templateOptions = input.required<{
    options: any;
    tokens: Array<any>;
  }>();
}
