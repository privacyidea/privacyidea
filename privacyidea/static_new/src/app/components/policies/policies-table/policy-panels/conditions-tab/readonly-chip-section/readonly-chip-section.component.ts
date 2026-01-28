import { Component, input } from "@angular/core";

@Component({
  selector: "app-readonly-chip-section",
  standalone: true,
  imports: [],
  templateUrl: "./readonly-chip-section.component.html",
  styleUrls: ["./readonly-chip-section.component.scss"]
})
export class ReadonlyChipSectionComponent {
  readonly label = input.required<string>();
  readonly values = input.required<string[]>();
  readonly marker = input<string>();
}
