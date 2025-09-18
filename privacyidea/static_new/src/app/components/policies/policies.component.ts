import { Component } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatExpansionModule } from "@angular/material/expansion";

@Component({
  selector: "app-policies",
  standalone: true,
  imports: [CommonModule, MatExpansionModule],
  templateUrl: "./policies.component.html",
  styleUrl: "./policies.component.scss"
})
export class PoliciesComponent {}
