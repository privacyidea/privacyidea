import { inject, Injectable, signal } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { toSignal } from "@angular/core/rxjs-interop";
import { map } from "rxjs";
import { PiResponse } from "../../models/pi-response";

export interface Policy {
  // Define the policy interface here
}

@Injectable({
  providedIn: "root"
})
export class PolicyService {
  http = inject(HttpClient);
  policyBaseUrl = "/policy/";

  allPolicies = toSignal(
    this.http.get<PiResponse<{ [key: string]: Policy }>>(this.policyBaseUrl).pipe(map((res) => Object.values(res.result.value)))
  );
}
