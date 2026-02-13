import { Component, input } from "@angular/core";

@Component({
  selector: "app-view-condition-section",
  standalone: true,
  imports: [],
  templateUrl: "./view-condition-section.component.html",
  styleUrls: ["./view-condition-section.component.scss"]
})
export class ViewConditionSectionComponent {
  readonly label = input.required<string>();
  readonly values = input.required<string[]>();
  readonly marker = input<string>();
}
