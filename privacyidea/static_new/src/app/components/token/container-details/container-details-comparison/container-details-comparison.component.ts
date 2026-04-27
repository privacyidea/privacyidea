import { Component, input } from "@angular/core";
import { TemplateComparisonResult } from "src/app/services/container/container.service";

@Component({
  selector: "app-container-details-comparison",
  templateUrl: "container-details-comparison.component.html"
})
export class ContainerDetailsComparison {
  readonly comparisonResult = input.required<TemplateComparisonResult>();
}
