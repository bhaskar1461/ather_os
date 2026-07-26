import SwiftUI

struct ProfilesView: View {
    @State private var profiles: [UserProfile] = [
        UserProfile(
            id: "1", name: "Primary Self", relation: "You",
            birthDate: "2000-01-01", birthTime: "12:00",
            birthPlace: "Hyderabad, India", latitude: 17.3850, longitude: 78.4867,
            timezone: "Asia/Kolkata", isDefault: true
        )
    ]
    @State private var isAddingProfile: Bool = false
    @State private var newName: String = ""
    @State private var newRelation: String = "Friend"
    @State private var newBirthDate: String = "2000-01-01"
    @State private var newBirthTime: String = "12:00"
    @State private var newBirthPlace: String = "Hyderabad, India"

    var body: some View {
        NavigationView {
            List {
                Section(header: Text("Souls in Focus")) {
                    ForEach(profiles) { profile in
                        HStack(spacing: 12) {
                            Circle()
                                .fill(profile.isDefault ? Color.purple : Color.gray.opacity(0.3))
                                .frame(width: 36, height: 36)
                                .overlay(
                                    Text(profile.name.prefix(1).uppercased())
                                        .font(.headline.bold())
                                        .foregroundColor(.white)
                                )

                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(profile.name).bold()
                                    if profile.isDefault {
                                        Text("DEFAULT")
                                            .font(.system(size: 8, weight: .bold))
                                            .padding(.horizontal, 6)
                                            .padding(.vertical, 2)
                                            .background(Color.purple.opacity(0.2))
                                            .foregroundColor(.purple)
                                            .cornerRadius(4)
                                    }
                                }
                                Text("\(profile.relation) • \(profile.birthDate) (\(profile.birthPlace))")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
            .navigationTitle("Profiles")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { isAddingProfile = true }) {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $isAddingProfile) {
                NavigationView {
                    Form {
                        Section(header: Text("Profile Info")) {
                            TextField("Name", text: $newName)
                            Picker("Relationship", selection: $newRelation) {
                                Text("Self").tag("You")
                                Text("Partner").tag("Partner")
                                Text("Family").tag("Family")
                                Text("Friend").tag("Friend")
                            }
                        }

                        Section(header: Text("Birth Coordinates")) {
                            TextField("Birth Date (YYYY-MM-DD)", text: $newBirthDate)
                            TextField("Birth Time (HH:MM)", text: $newBirthTime)
                            TextField("Birth Place", text: $newBirthPlace)
                        }
                    }
                    .navigationTitle("Add Profile")
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Cancel") { isAddingProfile = false }
                        }
                        ToolbarItem(placement: .confirmationAction) {
                            Button("Save") {
                                let p = UserProfile(
                                    id: UUID().uuidString,
                                    name: newName.isEmpty ? "New Profile" : newName,
                                    relation: newRelation,
                                    birthDate: newBirthDate,
                                    birthTime: newBirthTime,
                                    birthPlace: newBirthPlace,
                                    latitude: 17.3850,
                                    longitude: 78.4867,
                                    timezone: "Asia/Kolkata",
                                    isDefault: false
                                )
                                profiles.append(p)
                                isAddingProfile = false
                                newName = ""
                            }
                        }
                    }
                }
            }
        }
    }
}
